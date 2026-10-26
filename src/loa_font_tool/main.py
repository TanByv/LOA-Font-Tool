import tkinter as tk
import traceback
from tkinter import messagebox


def main():
    try:
        from .app import FontModdingTool

        root = tk.Tk()
        FontModdingTool(root)
        root.mainloop()
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror(
            "Fatal Error", f"An unexpected error occurred on startup:\n{e}"
        )


if __name__ == "__main__":
    main()
