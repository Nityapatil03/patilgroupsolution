import sys
import os
import time
import random
import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, messagebox, ttk


class ChaiInterpreter:
    def __init__(self, functions=None, output_callback=None):
        self.variables = {}
        self.functions = functions if functions is not None else {}
        self.output_callback = output_callback if output_callback else print

    def log(self, message):
        self.output_callback(str(message) + "\n")

    def evaluate_expression(self, expr):
        expr = expr.strip()
        for var_name, var_val in self.variables.items():
            if isinstance(var_val, str):
                expr = expr.replace(var_name, f'"{var_val}"')
            else:
                expr = expr.replace(var_name, str(var_val))
        try:
            return eval(expr, {"__builtins__": None}, {})
        except Exception as e:
            raise ValueError(f"Expression evaluation error near '{expr}': {e}")

    def run(self, code_script):
        lines = code_script.strip().split("\n")
        self._run_block(lines, 0, len(lines))

    def _run_block(self, lines, start_idx, end_idx):
        i = start_idx
        while i < end_idx:
            line_num = i + 1
            line = lines[i].strip()

            if not line or line.startswith("#"):
                i += 1
                continue

            try:
                # 1. SIP (Print to GUI Console)
                if line.startswith("sip "):
                    content = line[4:].strip()
                    self.log(self.evaluate_expression(content))

                # 2. WAIT (Pause execution)
                elif line.startswith("wait "):
                    seconds = float(self.evaluate_expression(line[5:].strip()))
                    time.sleep(seconds)

                # 3. BREW (Variables, Input, and Random numbers)
                elif line.startswith("brew "):
                    assignment = line[5:].strip()
                    if "=" in assignment:
                        parts = assignment.split("=", 1)
                        var_name = parts[0].strip()
                        var_value = parts[1].strip()

                        if var_value.startswith("order "):
                            prompt = var_value[6:].strip().strip("\"'")
                            user_input = simpledialog.askstring("Chai Input", prompt)
                            if user_input is None:
                                user_input = ""

                            if user_input.replace('.', '', 1).isdigit():
                                self.variables[var_name] = float(user_input) if "." in user_input else int(user_input)
                            else:
                                self.variables[var_name] = user_input

                        elif var_value.startswith("random "):
                            try:
                                range_part = var_value[7:].strip()
                                range_split = range_part.split("to")
                                low = int(self.evaluate_expression(range_split[0].strip()))
                                high = int(self.evaluate_expression(range_split[1].strip()))
                                self.variables[var_name] = random.randint(low, high)
                            except Exception:
                                raise ValueError(f"Invalid random range format. Use: random X to Y")
                        else:
                            self.variables[var_name] = self.evaluate_expression(var_value)

                # 4. STEEP / UNSTEEP (If / Else Statements with Nested Support)
                elif line.startswith("steep "):
                    condition = line[6:].strip()

                    block_start = i + 1
                    depth = 1
                    i += 1
                    while i < end_idx:
                        curr = lines[i].strip()
                        if curr.startswith("steep "):
                            depth += 1
                        elif curr == "endsteep":
                            depth -= 1
                            if depth == 0:
                                break
                        i += 1

                    if depth > 0:
                        raise SyntaxError("Missing 'endsteep' keyword.")

                    block_end = i
                    sub_lines = lines[block_start:block_end]

                    if_lines = []
                    else_lines = []
                    in_else = False
                    sub_depth = 0

                    for sub_line in sub_lines:
                        sl_stripped = sub_line.strip()
                        if sl_stripped.startswith("steep "):
                            sub_depth += 1
                        elif sl_stripped == "endsteep":
                            sub_depth -= 1

                        if sub_depth == 0 and sl_stripped == "unsteep":
                            in_else = True
                            continue

                        if in_else:
                            else_lines.append(sub_line)
                        else:
                            if_lines.append(sub_line)

                    if self.evaluate_expression(condition):
                        if if_lines:
                            self._run_block(if_lines, 0, len(if_lines))
                    else:
                        if else_lines:
                            self._run_block(else_lines, 0, len(else_lines))

                # 5. REFILL (While Loop)
                elif line.startswith("refill "):
                    condition = line[7:].strip()
                    block_start = i + 1
                    depth = 1
                    i += 1
                    while i < end_idx:
                        curr = lines[i].strip()
                        if curr.startswith("refill "):
                            depth += 1
                        elif curr == "endrefill":
                            depth -= 1
                            if depth == 0:
                                break
                        i += 1

                    if depth > 0:
                        raise SyntaxError("Missing 'endrefill' keyword.")

                    block_end = i
                    loop_lines = lines[block_start:block_end]

                    while self.evaluate_expression(condition):
                        self._run_block(loop_lines, 0, len(loop_lines))

                # 6. RECIPE (Function Definition)
                elif line.startswith("recipe "):
                    header = line[7:].strip()
                    if "(" not in header or ")" not in header:
                        raise SyntaxError("Invalid recipe header format. Use: recipe name(arg)")

                    func_name = header.split("(")[0].strip()
                    arg_name = header.split("(")[1].split(")")[0].strip()

                    block_start = i + 1
                    depth = 1
                    i += 1
                    while i < end_idx:
                        curr = lines[i].strip()
                        if curr.startswith("recipe "):
                            depth += 1
                        elif curr == "endrecipe":
                            depth -= 1
                            if depth == 0:
                                break
                        i += 1

                    if depth > 0:
                        raise SyntaxError("Missing 'endrecipe' keyword.")

                    block_end = i
                    self.functions[func_name] = {"arg": arg_name, "body": lines[block_start:block_end]}

                # 7. SERVE (Function Call)
                elif line.startswith("serve "):
                    call_expr = line[6:].strip()
                    if "(" not in call_expr or ")" not in call_expr:
                        raise SyntaxError("Invalid recipe call format. Use: serve name(val)")

                    func_name = call_expr.split("(")[0].strip()
                    arg_val = call_expr.split("(")[1].split(")")[0].strip()

                    if func_name in self.functions:
                        func_data = self.functions[func_name]
                        func_interpreter = ChaiInterpreter(self.functions, self.output_callback)
                        func_interpreter.variables = self.variables.copy()
                        func_interpreter.variables[func_data["arg"]] = self.evaluate_expression(arg_val)
                        func_interpreter._run_block(func_data["body"], 0, len(func_data["body"]))
                        self.variables.update(func_interpreter.variables)
                    else:
                        raise NameError(f"Unknown recipe '{func_name}'")

                else:
                    raise SyntaxError(f"Unknown statement keyword: '{line}'")

            except Exception as e:
                raise RuntimeError(f"Error on Line {line_num} ('{line}'): {str(e)}")

            i += 1


# --- Graphical User Interface (GUI) ---
class ChaiIDE:
    def __init__(self, root, file_to_open=None):
        self.root = root
        self.root.title("Chai Language Studio ☕")
        self.root.geometry("1150x750")

        self.profile_name = "ChaiDeveloper"
        self.current_theme = "Default (Chai)"

        self.themes = {
            "Default (Chai)": {
                "root_bg": "#2b1d12", "menu_bg": "#3e2723", "menu_fg": "white",
                "editor_bg": "#3e2723", "editor_fg": "#ffffff", "editor_insert": "white",
                "console_bg": "#1e120b", "console_fg": "#a5d6a7", "label_fg": "#ffecd2",
                "btn_bg": "#ff7043", "btn_fg": "white", "status_bg": "#1e120b", "status_fg": "#ffecd2",
                "line_bg": "#301e15", "line_fg": "#8d6e63"
            },
            "Dark Mode": {
                "root_bg": "#121212", "menu_bg": "#1f1f1f", "menu_fg": "#ffffff",
                "editor_bg": "#1e1e1e", "editor_fg": "#d4d4d4", "editor_insert": "white",
                "console_bg": "#000000", "console_fg": "#4ec9b0", "label_fg": "#cccccc",
                "btn_bg": "#0e639c", "btn_fg": "white", "status_bg": "#007acc", "status_fg": "white",
                "line_bg": "#252526", "line_fg": "#858585"
            },
            "Light Mode": {
                "root_bg": "#f5f2eb", "menu_bg": "#e6dfd3", "menu_fg": "#2b1d12",
                "editor_bg": "#ffffff", "editor_fg": "#000000", "editor_insert": "black",
                "console_bg": "#faf7f2", "console_fg": "#2e7d32", "label_fg": "#2b1d12",
                "btn_bg": "#d84315", "btn_fg": "white", "status_bg": "#e6dfd3", "status_fg": "#2b1d12",
                "line_bg": "#eee8df", "line_fg": "#795548"
            }
        }

        self.menubar = tk.Menu(root)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="New File", command=self.new_file)
        self.file_menu.add_command(label="New Window", command=self.new_window)
        self.file_menu.add_command(label="New Project", command=self.new_project)
        self.file_menu.add_command(label="Recent project", command=self.Recent_project_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Open File...", command=self.open_file)
        self.file_menu.add_command(label="Save File...", command=self.save_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=root.quit)
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.view_menu.add_command(label="Clear Console", command=self.clear_console)
        self.menubar.add_cascade(label="View", menu=self.view_menu)

        self.settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.settings_menu.add_command(label="Preferences & Settings", command=self.open_settings_window)
        self.menubar.add_cascade(label="Settings", menu=self.settings_menu)

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label="Chai Language Syntax Docs", command=self.show_docs)
        self.help_menu.add_command(label="About Chai Studio", command=self.show_about)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        root.config(menu=self.menubar)

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left Side: Code Editor
        self.editor_frame = tk.Frame(self.main_frame)
        self.editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.editor_label = tk.Label(self.editor_frame, text="Chai Script Editor:", font=("Arial", 10, "bold"))
        self.editor_label.pack(anchor="w")

        editor_inner_frame = tk.Frame(self.editor_frame)
        editor_inner_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.line_numbers = tk.Text(editor_inner_frame, width=4, padx=4, takefocus=0, borderwidth=0,
                                    font=("Courier New", 11), state="disabled")
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.code_text = scrolledtext.ScrolledText(editor_inner_frame, wrap=tk.WORD, font=("Courier New", 11))
        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.code_text.bind("<<Change>>", self.update_line_numbers)
        self.code_text.bind("<KeyRelease>", self.update_line_numbers)
        self.code_text.bind("<MouseWheel>", self.update_line_numbers)
        self.code_text.bind("<Button-1>", self.update_line_numbers)

        self.run_btn = tk.Button(self.editor_frame, text="🔥 Brew Code (Run)", command=self.run_code,
                                 font=("Arial", 11, "bold"), relief=tk.RAISED, bd=3)
        self.run_btn.pack(fill=tk.X, pady=2)

        # Right Side: Console Output Panel (Terminal bar fully removed)
        self.right_container = tk.Frame(self.main_frame)
        self.right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self.console_frame = tk.Frame(self.right_container)
        self.console_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        self.console_label = tk.Label(self.console_frame, text="Console Output:", font=("Arial", 10, "bold"))
        self.console_label.pack(anchor="w")

        self.output_text = scrolledtext.ScrolledText(self.console_frame, wrap=tk.WORD, font=("Courier New", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=2)

        self.status_bar = tk.Label(root, text="Status: Ready to brew ☕", font=("Arial", 9), anchor="w", padx=10)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.apply_theme(self.current_theme)

        if file_to_open and os.path.exists(file_to_open):
            with open(file_to_open, "r") as f:
                code = f.read()
            self.code_text.insert(tk.END, code)
        else:
            self.Recent_project_file()

        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        lines_count = self.code_text.get("1.0", tk.END).count("\n")
        line_string = "\n".join(str(i) for i in range(1, lines_count))

        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)
        self.line_numbers.insert("1.0", line_string)
        self.line_numbers.config(state=tk.DISABLED)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        t = self.themes[theme_name]

        self.root.configure(bg=t["root_bg"])
        self.main_frame.configure(bg=t["root_bg"])
        self.editor_frame.configure(bg=t["root_bg"])
        self.right_container.configure(bg=t["root_bg"])
        self.console_frame.configure(bg=t["root_bg"])

        self.editor_label.configure(bg=t["root_bg"], fg=t["label_fg"])
        self.console_label.configure(bg=t["root_bg"], fg=t["label_fg"])

        self.code_text.configure(bg=t["editor_bg"], fg=t["editor_fg"], insertbackground=t["editor_insert"])
        self.line_numbers.configure(bg=t["line_bg"], fg=t["line_fg"])
        self.output_text.configure(bg=t["console_bg"], fg=t["console_fg"], insertbackground=t["editor_insert"])

        self.run_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"])
        self.status_bar.configure(bg=t["status_bg"], fg=t["status_fg"])

        self.menubar.config(bg=t["menu_bg"], fg=t["menu_fg"])

    def open_settings_window(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Chai Studio Settings ⚙️")
        settings_win.geometry("380x280")
        settings_win.configure(bg=self.themes[self.current_theme]["root_bg"])
        settings_win.grab_set()

        t = self.themes[self.current_theme]

        tk.Label(settings_win, text="Studio Preferences", font=("Arial", 12, "bold"), fg=t["label_fg"],
                 bg=t["root_bg"]).pack(pady=10)

        tk.Label(settings_win, text="User Profile Name:", font=("Arial", 9, "bold"), fg=t["label_fg"],
                 bg=t["root_bg"]).pack(anchor="w", padx=20)
        name_entry = tk.Entry(settings_win, font=("Arial", 10), bg="#ffffff", fg="#000000")
        name_entry.insert(0, self.profile_name)
        name_entry.pack(fill=tk.X, padx=20, pady=5)

        tk.Label(settings_win, text="Select Theme Mode:", font=("Arial", 9, "bold"), fg=t["label_fg"],
                 bg=t["root_bg"]).pack(anchor="w", padx=20, pady=(10, 0))

        theme_var = tk.StringVar(value=self.current_theme)
        theme_combo = ttk.Combobox(settings_win, textvariable=theme_var, values=list(self.themes.keys()),
                                   state="readonly", font=("Arial", 10))
        theme_combo.pack(fill=tk.X, padx=20, pady=5)

        def save_settings():
            self.profile_name = name_entry.get().strip() or "ChaiDeveloper"
            selected_theme = theme_var.get()
            self.apply_theme(selected_theme)
            settings_win.destroy()
            self.status_bar.config(text="Status: Settings updated successfully! ✨")

        save_btn = tk.Button(settings_win, text="Save Settings", command=save_settings, bg=t["btn_bg"], fg=t["btn_fg"],
                             font=("Arial", 10, "bold"))
        save_btn.pack(pady=15)

    def new_file(self):
        self.code_text.delete(1.0, tk.END)
        self.update_line_numbers()
        self.status_bar.config(text="Status: Created new file")

    def new_window(self):
        new_win = tk.Toplevel(self.root)
        ChaiIDE(new_win)

    def new_project(self):
        if messagebox.askyesno("New Project", "Create a new project workspace? Unsaved changes will be lost."):
            self.code_text.delete(1.0, tk.END)
            self.output_text.delete(1.0, tk.END)
            self.update_line_numbers()
            self.status_bar.config(text="Status: New project initialized")

    def Recent_project_file(self):
        recent_project_code = """# --- PROJECT: CHAI CAFE MANAGEMENT SYSTEM ---
sip "=========================================="
sip "     ☕ WELCOME TO CHAI CAFE MANAGER     "
sip "=========================================="

# 1. Take Manager Profile Details
brew manager_name = order "Enter Manager Name:"
sip "Administrator Active:"
sip manager_name
wait 1.0

# 2. Define a Recipe for Serving Daily Specials
recipe announce_special(flavor_name)
    sip "------------------------------------------"
    sip "✨ TODAY'S FEATURED SPECIAL BREW ✨"
    sip flavor_name
    sip "------------------------------------------"
endrecipe

# 3. Randomly select today's special from a roll
brew special_roll = random 1 to 3

steep special_roll == 1
    brew current_special = "Royal Saffron Masala Chai"
unsteep
    steep special_roll == 2
        brew current_special = "Kulhad Ginger Decoction"
    unsteep
        brew current_special = "Cardamom Green Tea Infusion"
    endsteep
endsteep

# Call our function
serve announce_special(current_special)
wait 1.5

# 4. Process customer order queue using a loop (Refill)
brew customer_queue = order "How many customers are waiting in line?"

sip "Processing customer queue..."
wait 1.0

brew served_count = 1
refill customer_queue > 0
    sip "Serving cup to customer number:"
    sip served_count

    # Nested check for VIP customers based on random chance
    brew vip_chance = random 1 to 5
    steep vip_chance == 5
        sip "⭐ VIP Status Detected! Added free biscuits."
    unsteep
        sip "Standard service completed."
    endsteep

    brew customer_queue = customer_queue - 1
    brew served_count = served_count + 1
    wait 0.4
endrefill

sip "=========================================="
sip "🎉 All customers served successfully!"
sip "Cafe shift closed by manager:"
sip manager_name
sip "=========================================="
"""
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(tk.END, recent_project_code)
        self.update_line_numbers()
        self.status_bar.config(text="Status: Loaded Recent Project")

    def open_file(self):
        file_path = filedialog.askopenfilename(defaultextension=".chai",
                                               filetypes=[("Chai Files", "*.chai"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "r") as f:
                code = f.read()
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(tk.END, code)
            self.update_line_numbers()
            self.status_bar.config(text=f"Loaded: {os.path.basename(file_path)}")

    def save_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".chai",
                                                 filetypes=[("Chai Files", "*.chai"), ("All Files", "*.*")])
        if file_path:
            with open(file_path, "w") as f:
                f.write(self.code_text.get(1.0, tk.END))
            self.status_bar.config(text=f"Saved: {os.path.basename(file_path)}")

    def clear_console(self):
        self.output_text.delete(1.0, tk.END)

    def show_docs(self):
        docs = """--- CHAI LANGUAGE SYNTAX GUIDE ---
1. sip [text/var] -> Prints to console.
2. brew [var] = [value] -> Creates/assigns variables.
3. brew [var] = order "prompt" -> Takes user input dialog.
4. brew [var] = random X to Y -> Generates random numbers.
5. wait [seconds] -> Pauses execution.
6. steep [condition] ... unsteep ... endsteep -> If/Else statements.
7. refill [condition] ... endrefill -> While loops.
8. recipe name(arg) ... endrecipe -> Functions.
9. serve name(val) -> Calls functions."""
        messagebox.showinfo("Chai Documentation", docs)

    def show_about(self, event=None):
        messagebox.showinfo("About Chai Studio", "Chai Language Studio v3.3\nClean Interface without Terminal Bar.")

    def append_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def run_code(self):
        self.output_text.delete(1.0, tk.END)
        self.status_bar.config(text="Status: Brewing code... ⏳")
        self.root.update()

        code = self.code_text.get(1.0, tk.END)
        interpreter = ChaiInterpreter(output_callback=self.append_output)
        try:
            interpreter.run(code)
            self.status_bar.config(text=f"Status: Brew complete! Enjoy your Chai, {self.profile_name} ☕")
        except Exception as e:
            self.append_output(f"\n❌ {str(e)}\n")
            self.status_bar.config(text="Status: Error during brewing ❌")


if __name__ == "__main__":
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    app = ChaiIDE(root, file_to_open=file_arg)
    root.mainloop()