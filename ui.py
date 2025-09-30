import tkinter as tk
from tkinter import ttk
import webbrowser

class AppUI:
    def __init__(self, root, app_controller):
        self.root = root
        self.app = app_controller
        self.setup_ui()

    def open_github_link(self, event):
        webbrowser.open_new("https://github.com/TanByv/loa-font-tool")

    def setup_ui(self):
        # --- Main container ---
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=0)
        main_container.rowconfigure(0, weight=1)

        # --- Left Side ---
        left_frame = ttk.Frame(main_container, padding="5")
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(1, weight=1)
        
        ttk.Label(left_frame, text="File Selection", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)
        
        ttk.Label(left_frame, text="QuickBMS 4GB Executable:").grid(row=1, column=0, sticky=tk.W, padx=(20, 10))
        ttk.Entry(left_frame, textvariable=self.app.quickbms_path, width=40).grid(row=1, column=1, padx=5)
        ttk.Button(left_frame, text="Browse", command=self.app.browse_quickbms).grid(row=1, column=2, padx=5)
        
        ttk.Label(left_frame, text="Original Archive (font.lpk):").grid(row=2, column=0, sticky=tk.W, padx=(20, 10), pady=(5, 0))
        ttk.Entry(left_frame, textvariable=self.app.input_archive_path, width=40).grid(row=2, column=1, padx=5, pady=(5, 0))
        ttk.Button(left_frame, text="Browse", command=self.app.browse_archive).grid(row=2, column=2, padx=5, pady=(5, 0))
        
        ttk.Label(left_frame, text="New TTF Font File:").grid(row=3, column=0, sticky=tk.W, padx=(20, 10), pady=(5, 0))
        ttk.Entry(left_frame, textvariable=self.app.ttf_file_path, width=40).grid(row=3, column=1, padx=5, pady=(5, 0))
        ttk.Button(left_frame, text="Browse", command=self.app.browse_ttf).grid(row=3, column=2, padx=5, pady=(5, 0))
        
        lang_frame = ttk.Frame(left_frame)
        lang_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), padx=(20, 0), sticky=tk.W)
        ttk.Label(lang_frame, text="Language:").grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(lang_frame, text="English", variable=self.app.language, value="English").grid(row=0, column=1, padx=(0, 10))
        ttk.Radiobutton(lang_frame, text="Spanish", variable=self.app.language, value="Spanish").grid(row=0, column=2)
        
        ttk.Separator(left_frame, orient='horizontal').grid(row=5, column=0, columnspan=3, sticky="we", pady=20)
        
        # --- FontMap Configuration ---
        ttk.Label(left_frame, text="FontMap Configuration", font=('Arial', 12, 'bold')).grid(row=6, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)
        
        fontmap_frame = ttk.LabelFrame(left_frame, text="Font Entries (leave empty to exclude attribute, default values are already filled in)", padding="10")
        fontmap_frame.grid(row=7, column=0, columnspan=3, sticky="we", padx=(20, 0), pady=(0, 10))
        
        ttk.Label(fontmap_frame, text="Font Key", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5)
        ttk.Label(fontmap_frame, text="Size Correction", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=5)
        ttk.Label(fontmap_frame, text="Leading Correction", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5)
        
        font_keys = [('$YG760', 'YG760'), ('$YG760_12pt', 'YG760_12pt'), ('$YG330', 'YG330'), ('$YoonGasiIIM', 'YoonGasiIIM'), ('$YoonGasiIIM_Small2pt', 'YoonGasiIIM_Small2pt')]
        for i, (display_name, key) in enumerate(font_keys, start=1):
            ttk.Label(fontmap_frame, text=display_name).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            ttk.Entry(fontmap_frame, textvariable=self.app.fontmap_configs[key]['size_correction'], width=20).grid(row=i, column=1, padx=5, pady=2)
            ttk.Entry(fontmap_frame, textvariable=self.app.fontmap_configs[key]['leading_correction'], width=20).grid(row=i, column=2, padx=5, pady=2)
        
        ttk.Separator(left_frame, orient='horizontal').grid(row=8, column=0, columnspan=3, sticky="we", pady=10)
        
        # --- Action Buttons ---
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=9, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Create Modded LPK", command=self.app.start_modding).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Insert to Game", command=self.app.insert_to_game).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Revert to Original", command=self.app.revert_to_original).grid(row=0, column=2, padx=5)
        
        # --- Progress Log ---
        self.app.progress_text = tk.Text(left_frame, height=8, width=55, wrap=tk.WORD)
        self.app.progress_text.grid(row=10, column=0, columnspan=3, pady=(10, 0), sticky="we")
        
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.app.progress_text.yview)
        scrollbar.grid(row=10, column=3, sticky="ns", pady=(10, 0))
        self.app.progress_text.configure(yscrollcommand=scrollbar.set)
        
        # --- Right Side ---
        right_frame = ttk.Frame(main_container, padding="10")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        
        instructions_frame = ttk.LabelFrame(right_frame, text="Usage Instructions", padding="10")
        instructions_frame.pack(fill="both", expand=True)
        
        instructions_content = "1. Setup Requirements\n• Download QuickBMS\n• Extract quickbms_4gb_files.exe\n\n2. File Selection\n• Browse and select all three files.\n• Select your game language.\n• Original archive can be found in 'Lost Ark\\EFGame' folder. (Steam -> Lost Ark -> Properties -> Installed Files -> Browse)\n\n3. FontMap Config\n• Adjust size/spacing if needed.\n• Size correction controls font size:\n    eg. 120 -> x1.2 of original size.\n    eg. 80 -> x0.8 of original size.\n• Leading correction controls space between lines:\n    eg. 200 -> More space between lines of text.\n    eg. -200 -> Less space between lines of text.\n\n4. Create & Install\n• Click 'Create Modded LPK' and save.\n• Click 'Insert to Game' to apply it.\n• You can skip 'Create Modded LPK' if you already have a modded LPK archive to use.\n• The original 'font.lpk' file will be automatically backed up as 'font.lpk.bak'\n\n5. Reverting\n• Click 'Revert to Original'."
        
        instructions_label = ttk.Label(instructions_frame, text=instructions_content, wraplength=280, justify=tk.LEFT)
        instructions_label.pack(anchor="nw")

        info_frame = ttk.Frame(right_frame)
        info_frame.pack(side="bottom", fill="x", pady=(10,0))
        
        ttk.Label(info_frame, text="Version: v1.2").pack(side="left")
        github_link = ttk.Label(info_frame, text="GitHub Repository", foreground="blue", cursor="hand2")
        github_link.pack(side="right")
        github_link.bind("<Button-1>", self.open_github_link)
