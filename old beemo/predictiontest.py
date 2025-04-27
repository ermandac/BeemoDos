import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from QNQpredictor import QNQpredictor, handle_feedback

class ModelTesterUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Keras Model Tester, Feedback & Retrainer")
        
        # Label to instruct user to select PNG files
        self.instruction_label = tk.Label(
            self.root,
            text="Select PNG files to test the prediction and retraining."
        )
        self.instruction_label.pack(pady=5)
        
        # Button to select files (focusing on PNG files)
        self.select_button = tk.Button(
            self.root,
            text="Select PNG Files",
            command=self.select_files
        )
        self.select_button.pack(pady=5)
        
        # Listbox displaying the selected file paths
        self.listbox = tk.Listbox(self.root, width=80)
        self.listbox.pack(pady=5)
        
        # Button to run prediction on the selected file (active selection)
        self.predict_button = tk.Button(
            self.root,
            text="Run Prediction",
            command=self.run_prediction
        )
        self.predict_button.pack(pady=5)
        
        # Button to provide feedback and retrain the model if needed
        self.feedback_button = tk.Button(
            self.root,
            text="Provide Feedback & Retrain",
            command=self.provide_feedback
        )
        self.feedback_button.pack(pady=5)
        
        # Text widget to display outputs and logging messages
        self.output_text = tk.Text(self.root, width=80, height=15)
        self.output_text.pack(pady=5)
        
        self.root.mainloop()
    
    def select_files(self):
        # Open file dialog allowing PNG selection (you can extend to other image formats)
        file_paths = filedialog.askopenfilenames(
            title="Select PNG Files", 
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file_paths:
            self.listbox.delete(0, tk.END)
            for path in file_paths:
                self.listbox.insert(tk.END, path)
    
    def run_prediction(self):
        # Clear output area
        self.output_text.delete("1.0", tk.END)
        if self.listbox.size() == 0:
            messagebox.showwarning("No File Selected", "Please select a PNG file for prediction.")
            return
            
        # Use the active (selected) file for prediction
        file_path = self.listbox.get(tk.ACTIVE)
        try:
            # Call QNQpredictor with the file path and pass the output_text widget so that prediction output is shown in the GUI.
            predicted_class, confidence, f1, precision = QNQpredictor(file_path, self.output_text)
            self.output_text.insert(tk.END, f"\nPrediction complete for {os.path.basename(file_path)}.\n")
        except Exception as e:
            self.output_text.insert(tk.END, f"Error during prediction: {e}\n")
    
    def provide_feedback(self):
        if self.listbox.size() == 0:
            messagebox.showwarning("No File Selected", "Please select a file before providing feedback.")
            return

        file_path = self.listbox.get(tk.ACTIVE)
        
        # Ask the user if the prediction was correct.
        # The Yes/No dialogue returns True for Yes and False for No.
        is_correct = messagebox.askyesno("Feedback", "Was the prediction correct?")
        
        # If correct, we call feedback handler with "correct"
        if is_correct:
            self.output_text.insert(tk.END, "Feedback: Prediction was correct. No retraining is needed.\n")
            handle_feedback(file_path, self.output_text, "correct")
        else:
            self.output_text.insert(tk.END, "Feedback: Prediction was incorrect. Initiating retraining...\n")
            handle_feedback(file_path, self.output_text, "incorrect")

if __name__ == "__main__":
    ModelTesterUI()
