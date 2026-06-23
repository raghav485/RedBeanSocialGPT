import os
import sys
import threading

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TKINTER_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    tk = None
    ttk = None
    messagebox = None
    TKINTER_IMPORT_ERROR = exc

from main import register_account, load_settings, load_profile, generate_random_username, generate_random_password
from src.temp_mail import TempMail
from src.proxy_manager import ProxyManager
from src.sites import get_available_site_names

def require_tkinter():
    if TKINTER_IMPORT_ERROR:
        raise RuntimeError(
            "Tkinter is not available in this Python installation. "
            "Install a Python build with Tk support to use the GUI, or run the CLI with main.py."
        ) from TKINTER_IMPORT_ERROR

class TextRedirector:
    """Redirects stdout to a tkinter text widget."""
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str_val):
        if not str_val:
            return

        def append_text():
            self.widget.configure(state="normal")
            self.widget.insert("end", str_val, (self.tag,))
            self.widget.see("end")
            self.widget.configure(state="disabled")

        try:
            self.widget.after(0, append_text)
        except RuntimeError:
            pass

    def flush(self):
        pass

class AccountGeneratorApp:
    def __init__(self, root):
        require_tkinter()
        self.root = root
        self.root.title("RedBeanSocialGPT - Account Generator")
        self.root.geometry("650x550")
        self.root.minsize(550, 450)
        
        # Load default settings
        self.settings = load_settings()
        self.settings.setdefault("site_config_dir", "config/sites")
        self.profile = load_profile("config/business_profile.json")
        self.site_names = get_available_site_names(self.settings.get("site_config_dir", "config/sites"))
        
        self.create_widgets()
        
        # Redirect standard stdout to Text log widget
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text, "stderr")

    def create_widgets(self):
        # Master Style
        style = ttk.Style()
        style.theme_use('clam')

        # Frame container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Platform Select
        platform_frame = ttk.LabelFrame(main_frame, text=" 1. Select Platform ", padding="10")
        platform_frame.pack(fill="x", pady=5)
        
        ttk.Label(platform_frame, text="Target Website:").pack(side="left", padx=5)
        default_site = self.site_names[0] if self.site_names else "reddit"
        self.platform_var = tk.StringVar(value=default_site)
        platform_combo = ttk.Combobox(
            platform_frame, 
            textvariable=self.platform_var, 
            values=self.site_names, 
            state="readonly"
        )
        platform_combo.pack(side="left", padx=5, fill="x", expand=True)

        # Settings Configuration
        config_frame = ttk.LabelFrame(main_frame, text=" 2. Generation Settings ", padding="10")
        config_frame.pack(fill="x", pady=5)

        # Number of Accounts
        ttk.Label(config_frame, text="Number of Accounts:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.num_accounts_var = tk.StringVar(value="1")
        num_entry = ttk.Entry(config_frame, textvariable=self.num_accounts_var, width=10)
        num_entry.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        # Use accounts.txt vs Free Temp Mail
        self.mail_mode_var = tk.BooleanVar(value=True)
        mail_check = ttk.Checkbutton(
            config_frame, 
            text="Use Free Temp-Mail API (Auto-registers names/emails)", 
            variable=self.mail_mode_var
        )
        mail_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=5, padx=5)

        # Headless mode
        self.headless_var = tk.BooleanVar(value=False)
        headless_check = ttk.Checkbutton(
            config_frame, 
            text="Run Headless Browser (Hide browser - WARNING: requires CAPTCHA API key)", 
            variable=self.headless_var
        )
        headless_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=5, padx=5)

        # Action Buttons
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.pack(fill="x", pady=5)

        self.generate_btn = ttk.Button(
            button_frame, 
            text="Start Generating Accounts", 
            command=self.start_generation
        )
        self.generate_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text=" 3. Execution Logs ", padding="10")
        log_frame.pack(fill="both", expand=True, pady=5)

        # Scrollable log area
        self.log_text = tk.Text(log_frame, wrap="word", state="disabled", height=15)
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def log_message(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_generation(self):
        # Validate inputs
        try:
            num = int(self.num_accounts_var.get())
            if num <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of accounts (integer > 0)")
            return

        self.generate_btn.configure(state="disabled")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        # Start registration thread to keep GUI responsive
        threading.Thread(target=self.run_generation_process, args=(num,), daemon=True).start()

    def run_generation_process(self, num_accounts):
        site_name = self.platform_var.get().lower()
        use_free_mail = self.mail_mode_var.get()
        is_headless = self.headless_var.get()
        
        # Load active configurations
        run_settings = self.settings.copy()
        run_settings["headless"] = is_headless
        run_settings["use_free_mail"] = use_free_mail

        # Initialize proxy manager
        proxy_manager = ProxyManager('proxy.txt')
        print(f"Loaded {len(proxy_manager.proxies)} proxies from proxy.txt")

        accounts_to_create = []

        # Read accounts if not using temp mail
        if not use_free_mail:
            accounts_file = 'accounts.txt'
            if os.path.exists(accounts_file) and os.path.getsize(accounts_file) > 0:
                with open(accounts_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ',' in line:
                            parts = line.split(',')
                            if len(parts) == 3:
                                u, p, e = parts
                                accounts_to_create.append((e.strip(), u.strip(), p.strip()))
            
            if not accounts_to_create:
                print("Warning: accounts.txt is empty or missing. Falling back to dynamic email generation.")
                run_settings["use_free_mail"] = True
                use_free_mail = True

        # Generate dynamically if list empty
        if not accounts_to_create:
            for _ in range(num_accounts):
                temp_mail = TempMail()
                email = temp_mail.generate_email()
                username = generate_random_username()
                password = generate_random_password()
                accounts_to_create.append((email, username, password))

        success_count = 0
        for email, username, password in accounts_to_create[:num_accounts]:
            # Rotate proxy
            selected_proxy = proxy_manager.get_random_proxy()
            
            # Setup GUI callback popup to alert user on captcha
            def captcha_alert_callback():
                messagebox.showwarning("CAPTCHA Required", f"A security challenge has been detected. Please solve the CAPTCHA in the open browser window, then click OK to continue.")

            # Run registration
            is_success = register_account(
                site_name,
                email,
                username,
                password,
                run_settings,
                selected_proxy,
                extra_context=self.profile
            )
            
            if is_success:
                success_count += 1
                print(f"Success! Account successfully created: {username}")
                # Save output to CSV
                output_csv = run_settings.get("output_csv", "accounts.csv")
                file_exists = os.path.exists(output_csv)
                import csv
                with open(output_csv, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['Email', 'Username', 'Password', 'Site'])
                    writer.writerow([email, username, password, site_name])
            else:
                print(f"Failed to create account: {username}")

        print(f"\nGeneration complete! Created {success_count}/{num_accounts} accounts.")
        self.root.after(0, lambda: self.generate_btn.configure(state="normal"))
        self.root.after(0, lambda: messagebox.showinfo("Completed", f"Completed generation. Successfully created {success_count}/{num_accounts} accounts."))

def main():
    try:
        require_tkinter()
    except RuntimeError as exc:
        print(exc)
        return 1

    root = tk.Tk()
    app = AccountGeneratorApp(root)
    root.mainloop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
