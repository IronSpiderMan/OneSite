// Bundle the real Arco components into the standalone Python editor. End users
// run site web without npm, a CDN, node_modules, or a separate assets directory.
import { build } from "esbuild";
import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const root = dirname(fileURLToPath(import.meta.url));
const result = await build({
  absWorkingDir: root,
  entryPoints: ["src/main.jsx"],
  bundle: true,
  minify: true,
  write: false,
  outdir: "dist",
  entryNames: "studio",
  target: ["es2020"],
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "eof",
  metafile: true,
});
// Keep the licenses for every dependency included in the offline bundle.
const packages = new Set(
  Object.keys(result.metafile.inputs).flatMap((path) => {
    const parts = path.split("node_modules/").at(-1).split("/");
    if (!path.includes("node_modules/")) return [];
    return [parts[0].startsWith("@") ? parts.slice(0, 2).join("/") : parts[0]];
  }),
);
const notices = [...packages]
  .sort()
  .map((name) => {
    const dir = resolve(root, "node_modules", name);
    const metadata = JSON.parse(
      readFileSync(resolve(dir, "package.json"), "utf8"),
    );
    const files = readdirSync(dir).filter((file) =>
      /^(licen[sc]e|copying|notice)(\.|$)/i.test(file),
    );
    const notice = files.length
      ? files.map((file) => readFileSync(resolve(dir, file), "utf8")).join("\n")
      : `License: ${metadata.license}\nAuthor: ${JSON.stringify(metadata.author)}\n${metadata.homepage || ""}`;
    return `${name} ${metadata.version}\n${notice}`;
  })
  .join("\n\n--------------------\n\n");
writeFileSync(resolve(root, "THIRD_PARTY_NOTICES.txt"), notices);
const encoded = [];
for (const file of result.outputFiles) {
  const ext = file.path.endsWith(".css") ? "css" : "js";
  const mime =
    ext === "css"
      ? "text/css; charset=utf-8"
      : "text/javascript; charset=utf-8";
  const content =
    ext === "js"
      ? Buffer.from(
          file.text + "\n/*\n" + notices.replaceAll("*/", "* /") + "\n*/\n",
        )
      : file.contents;
  const zipped = gzipSync(content, { level: 9 });
  const chunks = zipped
    .toString("base64")
    .match(/.{1,100}/g)
    .map((s) => `        "${s}"`)
    .join("\n");
  encoded.push(
    `    "/assets/studio.${ext}": ("${mime}", base64.b64decode(\n${chunks}\n    )),`,
  );
  console.log(
    `studio.${ext}: ${file.contents.length} bytes / ${zipped.length} gzip`,
  );
}
const python = resolve(root, "../webui.py");
const source = readFileSync(python, "utf8");
const start = "# BEGIN GENERATED ARCO ASSETS";
const end = "# END GENERATED ARCO ASSETS";
if (!source.includes(start) || !source.includes(end))
  throw Error("Missing WebUI asset markers");
const block = `${start}\n# Built by webui_frontend/build.mjs. Do not edit encoded assets.\n# fmt: off\nASSETS = {\n${encoded.join("\n")}\n}\n# fmt: on\n${end}`;
writeFileSync(
  python,
  source.slice(0, source.indexOf(start)) +
    block +
    source.slice(source.indexOf(end) + end.length),
);
