import tkinter as tk
from app import FontModdingTool

def main():
    try:
        root = tk.Tk()
        FontModdingTool(root)
        root.mainloop()
    except Exception as e:
        print(f"Failed to start the application: {e}")
        import tkinter.messagebox
        tkinter.messagebox.showerror("Fatal Error", f"An unexpected error occurred on startup:\n{e}")

if __name__ == "__main__":
    main()
