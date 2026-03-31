import { Toaster } from "sonner"

export const AppToaster = () => (
  <Toaster
    position="top-right"
    richColors
    toastOptions={{
      classNames: {
        toast:
          "bg-card/90 text-card-foreground border border-border shadow-md backdrop-blur-md",
        title: "text-sm font-semibold",
        description: "text-sm text-muted-foreground",
        actionButton:
          "bg-primary text-primary-foreground hover:bg-primary/90",
        cancelButton:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
      },
    }}
  />
)

