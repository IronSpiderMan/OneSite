use std::{fs, path::Path};

// Tauri requires default PNG/ICO files even when a project has not supplied
// branding yet. Generate a small deterministic placeholder before Tauri's
// build helper and context macro inspect the icon paths.
fn ensure_default_icons() {
    const PNG: &[u8] = &[
        137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 32, 0, 0,
        0, 32, 8, 6, 0, 0, 0, 115, 122, 122, 244, 0, 0, 0, 47, 73, 68, 65, 84, 120,
        218, 237, 206, 33, 1, 0, 0, 8, 3, 48, 10, 81, 141, 176, 20, 130, 24, 55, 19, 243,
        171, 158, 189, 164, 18, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
        72, 7, 30, 239, 151, 176, 136, 99, 109, 239, 240, 0, 0, 0, 0, 73, 69, 78, 68,
        174, 66, 96, 130,
    ];

    let icons = Path::new("icons");
    fs::create_dir_all(icons).expect("failed to create the Tauri icon directory");
    let png_path = icons.join("icon.png");
    if !png_path.exists() {
        fs::write(&png_path, PNG).expect("failed to write the default PNG icon");
    }

    let ico_path = icons.join("icon.ico");
    if !ico_path.exists() {
        let mut ico = vec![0, 0, 1, 0, 1, 0, 32, 32, 0, 0, 1, 0, 32, 0];
        ico.extend_from_slice(&(PNG.len() as u32).to_le_bytes());
        ico.extend_from_slice(&22_u32.to_le_bytes());
        ico.extend_from_slice(PNG);
        fs::write(ico_path, ico).expect("failed to write the default Windows icon");
    }
}

fn main() {
    ensure_default_icons();
    tauri_build::build()
}
