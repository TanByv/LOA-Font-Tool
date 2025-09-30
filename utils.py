import os
import sys
import ctypes
import base64
import subprocess
from tkinter import filedialog, messagebox

# --- Privilege and System Functions ---

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        print(f"Unknown error: {e}")
        return False

def find_game_directory():
    system_drive = os.environ.get("SYSTEMDRIVE", "C:")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", os.path.join(system_drive, "Program Files (x86)"))
    default_path = os.path.join(program_files_x86, "Steam", "steamapps", "common", "Lost Ark", "EFGame")

    if os.path.exists(os.path.join(default_path, "font.lpk")):
        return default_path

    messagebox.showinfo("Game Directory", "Lost Ark 'EFGame' folder not found. Please select it.")
    directory = filedialog.askdirectory(title="Select Lost Ark EFGame directory (containing font.lpk)")

    if directory and os.path.exists(os.path.join(directory, "font.lpk")):
        return directory
    elif directory:
        messagebox.showerror("Error", "Selected directory does not contain font.lpk")
    return None

# --- File and Script Generation ---

def create_fontmap_xml(fontmap_configs):
    xml_lines = ['<?xml version="1.0" encoding="utf-8"?>', '<FontMap>']
    font_keys = [('$YG760', 'YG760'), ('$YG760_12pt', 'YG760_12pt'), ('$YG330', 'YG330'), ('$YoonGasiIIM', 'YoonGasiIIM'), ('$YoonGasiIIM_Small2pt', 'YoonGasiIIM_Small2pt')]

    for display_name, key in font_keys:
        size_correction = fontmap_configs[key]['size_correction'].get().strip()
        leading_correction = fontmap_configs[key]['leading_correction'].get().strip()
        line = f'    <Item Key="{display_name}" File="ExuberanceF-Regular.ttf"'
        if size_correction: 
            line += f' SizeCorrectionRatio="{size_correction}"'
        if leading_correction: 
            line += f' LeadingCorrection="{leading_correction}"'
        line += ' />'
        xml_lines.append(line)

    xml_lines.append('</FontMap>')
    return '\n'.join(xml_lines)

def create_bms_script(target_index, working_dir):
    key_decoded = base64.b64decode("ODM2NTdlYTZmZmExZTY3MTM3NWM2ODlhMmU5OWE1OTg=").decode('utf-8')
    base_decoded = base64.b64decode("MTA2OWQ4ODczOGM1Yzc1ZjgyYjQ0YTFmMGEzODI3Njg=").decode('utf-8')
    
    script_content = f'''
        string ARCHIVE = "original.lpk"
        string KEY = "{key_decoded}"
        string BASE = "{base_decoded}"
        quickbmsver "0.12 -64"
        get FILE_NAME filename
        open FDSE ARCHIVE 1
        math ENTRY = 528
        string BASE h BASE
        get FILES long 1
        xmath SIZE "FILES * ENTRY"
        encryption blowfish KEY
        log MEMORY_FILE 4 SIZE 1
        encryption "" ""
        math MEM = -1
        math TARGET_INDEX = {target_index}
        math COUNT = 0
        for i = 0 < FILES
            get NAMEZ long MEM
            getdstring NAME NAMEZ MEM
            padding ENTRY MEM
            string NAME ! "\\"
            if i == TARGET_INDEX
                math COUNT = i
                padding ENTRY MEM
                goto -4 MEM SEEK_CUR
                get ENC long MEM
                print "Targeting file: %NAME%"
                break
            endif
        next i
        if COUNT != TARGET_INDEX
            print "Failed to find target file in the archive!"
            cleanexit
        endif
        xmath INFO_OFF "COUNT * ENTRY"
        log MEMORY_FILE2 INFO_OFF ENTRY MEM
        goto INFO_OFF MEM
        findloc OFFSET string NAME MEM ""
        putvarchr MEMORY_FILE OFFSET 0x5F315F31 long
        math FILES + 1
        append -1
            put FILES long MEM
        append
        append
            log MEMORY_FILE 0 ENTRY MEMORY_FILE2
        append
        get MODSIZE asize
        get SIZE asize MEM
        xmath INFO_OFF "SIZE - 12"
        if ENC = 0
            xmath CHECK "MODSIZE % 1024"
            if CHECK > 0
                print "\\nDatabase should be aligned to size multiple of 1024!"
                cleanexit
            endif
            putvarchr MEMORY_FILE INFO_OFF MODSIZE long
            math INFO_OFF + 4
            putvarchr MEMORY_FILE INFO_OFF MODSIZE long
            math INFO_OFF + 4
            putvarchr MEMORY_FILE INFO_OFF 0 long
        else
            comtype zlib_compress
            clog MEMORY_FILE5 0 MODSIZE MODSIZE
            get ZSIZE asize MEMORY_FILE5
            math ENSIZE = ZSIZE
            math ENSIZE x 8
            math OFFSET = ZSIZE
            for OFFSET = OFFSET < ENSIZE
                putvarchr MEMORY_FILE5 OFFSET 0
            next OFFSET
            putvarchr MEMORY_FILE INFO_OFF MODSIZE long
            math INFO_OFF + 4
            putvarchr MEMORY_FILE INFO_OFF ENSIZE long
            math INFO_OFF + 4
            putvarchr MEMORY_FILE INFO_OFF ZSIZE long
        endif
        math INFO_OFF + 4
        putvarchr MEMORY_FILE INFO_OFF 0 long
        string NAME = ARCHIVE
        string NAME % "."
        string NAME + "_mod.lpk"
        log NAME 0 4 MEM
        get FSIZE1 asize 1
        xmath OFF "(FILES - 1) * ENTRY + 8"
        math FSIZE1 - OFF
        append
            encryption blowfish KEY "" 1
            log NAME 4 SIZE MEM
            encryption "" ""
            log NAME OFF FSIZE1 1
            if ENC = 0
                callfunction get_key 1
                math CUR_OFF = 0
                math BLOCK = 1024
                for CUR_OFF = CUR_OFF < MODSIZE
                    encryption aes_256_cbc AES_KEY "" 1 32
                    log NAME CUR_OFF BLOCK
                    encryption "" ""
                    math CUR_OFF + BLOCK
                next
            else
                encryption blowfish KEY "" 1
                log NAME 0 ENSIZE MEMORY_FILE5
            endif
        append
        startfunction get_key
            log MEMORY_FILE10 0 0
            string TMP_NAME = FILE_NAME
            string TMP_NAME ! "_"
            string TMP_NAME % "."
            set TMP_NAME to_unicode TMP_NAME
            encryption md5 TMP_NAME
            encryption "" ""
            string MD = QUICKBMS_HASH
            for x = 0 < 16
                xmath TMP "15 - x"
                getvarchr K BASE x
                getvarchr M MD TMP
                math K ^ M
                putvarchr MEMORY_FILE10 x K
            next x
            getdstring AES_KEY 16 MEMORY_FILE10
            string AES_KEY 0b AES_KEY
            string AES_KEY l AES_KEY
            encryption sha256 AES_KEY
            encryption "" ""
            string AES_KEY 0= QUICKBMS_HASH
        endfunction'''
    script_path = os.path.join(working_dir, 'lpk-packing-script.bms')
    with open(script_path, 'w') as f:
        f.write(script_content)
    return script_path

# --- External Process Execution ---

def run_quickbms(quickbms_exe, script_path, input_file, working_dir, log_callback):
    cmd = [quickbms_exe, script_path, input_file, working_dir]
    
    creation_flags = 0
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NO_WINDOW
        
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=working_dir, 
            check=False,
            creationflags=creation_flags
        )
        if result.returncode != 0:
            log_callback(f"QuickBMS error: {result.stderr.strip()}")
            return False
        return True
    except FileNotFoundError:
        log_callback(f"Error: QuickBMS executable not found at '{quickbms_exe}'")
        return False
    except Exception as e:
        log_callback(f"An error occurred while running QuickBMS: {str(e)}")
        return False
