import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
import tempfile
from pathlib import Path
import ui
import utils

class FontModdingTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Lost Ark Font Modding Tool")
        self.root.geometry("875x675")

        self.quickbms_path = tk.StringVar()
        self.input_archive_path = tk.StringVar()
        self.ttf_file_path = tk.StringVar()
        self.last_created_mod = None
        self.language = tk.StringVar(value="English")

        # FontMap configuration variables
        self.fontmap_configs = {
            'YG760': {'size_correction': tk.StringVar(value=''), 'leading_correction': tk.StringVar(value='')},
            'YG760_12pt': {'size_correction': tk.StringVar(value='120'), 'leading_correction': tk.StringVar(value='')},
            'YG330': {'size_correction': tk.StringVar(value=''), 'leading_correction': tk.StringVar(value='')},
            'YoonGasiIIM': {'size_correction': tk.StringVar(value=''), 'leading_correction': tk.StringVar(value='-200')},
            'YoonGasiIIM_Small2pt': {'size_correction': tk.StringVar(value='120'), 'leading_correction': tk.StringVar(value='-200')}
        }
        
        self.progress_text = None
        self.ui = ui.AppUI(self.root, self)

    # --- UI Callback Methods ---

    def browse_quickbms(self):
        filename = filedialog.askopenfilename(
            title="Select QuickBMS executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.quickbms_path.set(filename)

    def browse_archive(self):
        filename = filedialog.askopenfilename(
            title="Select input archive",
            filetypes=[("LPK archives", "*.lpk"), ("All files", "*.*")]
        )
        if filename:
            self.input_archive_path.set(filename)

    def browse_ttf(self):
        filename = filedialog.askopenfilename(
            title="Select modified TTF file",
            filetypes=[("TrueType fonts", "*.ttf"), ("All files", "*.*")]
        )
        if filename:
            self.ttf_file_path.set(filename)

    def log_message(self, message):
        if self.progress_text:
            self.progress_text.insert(tk.END, message + "\n")
            self.progress_text.see(tk.END)
            self.root.update()
        else:
            print(message) 
            
    # --- Core Application Logic ---

    def get_target_indices(self):
        if self.language.get() == "English":
            return 4, 3
        else:  # Spanish
            return 21, 20

    def start_modding(self):
        if self.progress_text:
            self.progress_text.delete(1.0, tk.END)

        if not all([self.quickbms_path.get(), self.input_archive_path.get(), self.ttf_file_path.get()]):
            messagebox.showerror("Error", "Please select all required files (QuickBMS, LPK, and TTF).")
            return

        fontmap_index, font_index = self.get_target_indices()
        self.log_message(f"Language: {self.language.get()}")
        self.log_message(f"Target indices - FontMap: {fontmap_index}, Font: {font_index}")

        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            self.log_message(f"Created working directory: {working_dir}")
            try:
                self._process_archive_steps(working_dir, fontmap_index, font_index)
            except Exception as e:
                self.log_message(f"An unexpected error occurred: {str(e)}")
                messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

    def _process_archive_steps(self, working_dir, fontmap_index, font_index):
        # 1. Copy original archive
        original_lpk = working_dir / "original.lpk"
        shutil.copy2(self.input_archive_path.get(), original_lpk)
        self.log_message("Copied original archive to working directory")

        # 2. Create and insert FontMap.xml
        fontmap_path = working_dir / "FontMap.xml"
        fontmap_content = utils.create_fontmap_xml(self.fontmap_configs)
        with open(fontmap_path, 'w', encoding='utf-8') as f: 
            f.write(fontmap_content)
        self.log_message("Created FontMap.xml")
        
        script_path = utils.create_bms_script(fontmap_index, str(working_dir))
        self.log_message("Running QuickBMS for FontMap.xml...")
        if not utils.run_quickbms(self.quickbms_path.get(), script_path, str(fontmap_path), str(working_dir), self.log_message):
            messagebox.showerror("Error", "Failed to run QuickBMS for FontMap.xml")
            return
        self.log_message("Successfully inserted FontMap.xml")

        # 3. Prepare for second pass (TTF insertion)
        first_output = working_dir / "original_mod.lpk"
        if not first_output.exists():
            messagebox.showerror("Error", "First pass output not found")
            return
        os.remove(original_lpk)
        shutil.move(str(first_output), str(original_lpk))
        
        ttf_filename = os.path.basename(self.ttf_file_path.get())
        ttf_working_path = working_dir / ttf_filename
        shutil.copy2(self.ttf_file_path.get(), ttf_working_path)
        
        script_path = utils.create_bms_script(font_index, str(working_dir))
        self.log_message("Running QuickBMS for TTF file...")
        if not utils.run_quickbms(self.quickbms_path.get(), script_path, str(ttf_working_path), str(working_dir), self.log_message):
            messagebox.showerror("Error", "Failed to run QuickBMS for TTF file")
            return
        self.log_message("Successfully inserted TTF file")

        # 4. Save final output
        final_output = working_dir / "original_mod.lpk"
        if not final_output.exists():
            messagebox.showerror("Error", "Final output not found")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".lpk",
            filetypes=[("LPK archives", "*.lpk"), ("All files", "*.*")],
            initialfile="font.lpk",
            title="Save Modded LPK File"
        )
        if output_path:
            shutil.copy2(final_output, output_path)
            self.last_created_mod = output_path
            self.log_message(f"Saved final archive to: {output_path}")
            messagebox.showinfo("Success", f"Font mod created successfully!\nSaved to: {output_path}")
        else:
            self.log_message("Save operation cancelled by user")

    def insert_to_game(self):
        if self.progress_text:
            self.progress_text.delete(1.0, tk.END)
        self.log_message("Starting game installation process...")

        mod_file_path = self.last_created_mod
        if not (mod_file_path and os.path.exists(mod_file_path)):
             mod_file_path = filedialog.askopenfilename(
                    title="Select modded font.lpk file to install",
                    filetypes=[("LPK archives", "*.lpk"), ("All files", "*.*")]
                )
             if not mod_file_path:
                 self.log_message("No file selected, operation cancelled.")
                 return

        game_dir = utils.find_game_directory()
        if not game_dir: 
            return

        font_lpk_path = os.path.join(game_dir, "font.lpk")
        backup_path = os.path.join(game_dir, "font.lpk.bak")

        try:
            if not os.path.exists(backup_path):
                shutil.copy2(font_lpk_path, backup_path)
                self.log_message("Created backup: font.lpk.bak")
            
            shutil.copy2(mod_file_path, font_lpk_path)
            self.log_message("Successfully installed modded font!")
            messagebox.showinfo("Success", "Modded font has been successfully installed!")
        except PermissionError:
            messagebox.showwarning("Administrator Required", "Administrator privileges are required. Please restart as admin.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install mod: {str(e)}")

    def revert_to_original(self):
        if self.progress_text:
            self.progress_text.delete(1.0, tk.END)
        self.log_message("Starting revert process...")

        game_dir = utils.find_game_directory()
        if not game_dir: 
            return

        font_lpk_path = os.path.join(game_dir, "font.lpk")
        backup_path = os.path.join(game_dir, "font.lpk.bak")

        if not os.path.exists(backup_path):
            messagebox.showwarning("No Backup", "No backup file found. Please verify game files in Steam to restore.")
            return

        try:
            shutil.move(backup_path, font_lpk_path)
            self.log_message("Restored original font from backup.")
            messagebox.showinfo("Success", "Successfully reverted to original font!")
        except PermissionError:
            messagebox.showwarning("Administrator Required", "Administrator privileges are required. Please restart as admin.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to revert: {str(e)}")
