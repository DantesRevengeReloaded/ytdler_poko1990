import tkinter as tk

class AppUI:
    def __init__(self, root):
        self.root = root
        self.root.title("My App")
        self.root.geometry("600x600")
        self.root.resizable(True, True)
        self.root.grid_columnconfigure(0, weight=1)  # Make the first column expandable
        self.root.grid_columnconfigure(1, weight=1)  # Make the second column expandable
        self.root.grid_rowconfigure(0, weight=1)  # Make the first row expandable

        self.create_widgets()

    def create_widgets(self):
        label = tk.Label(self.root, text="Hello, World!", font=("Arial", 16))
        label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        button = tk.Button(self.root, text="Click Me!", command=self.button_clicked)
        button.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)  # Make the first column expandable
        self.root.grid_columnconfigure(1, weight=1)  # Make the second column expandable
        self.root.grid_rowconfigure(0, weight=1)  # Make the first row expandable
        button.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        for i in range(4):
            square_button = tk.Button(self.root, text=f"Button {i+1}", relief="solid", bd=0, bg="green", fg="white", padx=10, pady=5, borderwidth=0, highlightthickness=0)
            square_button.config(width=10, height=2, font=("Arial", 12, "bold"), highlightbackground="green")
            square_button.grid(row=2+i//2, column=i%2, padx=10, pady=10, sticky="nsew")

        left_label = tk.Label(self.root, text="Left Label", font=("Arial", 12))
        left_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")

        right_label = tk.Label(self.root, text="Right Label", font=("Arial", 12))
        right_label.grid(row=4, column=1, padx=10, pady=10, sticky="e")

    def button_clicked(self):
        # Add your code for button click event here
        pass

root = tk.Tk()
app = AppUI(root)
root.mainloop()



