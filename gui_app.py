import tkinter as tk
from tkinter import ttk  # Themed Tkinter widgets
from tkinter import messagebox, simpledialog
import datetime

# Import the backend functions
import store_manager_backend as backend

# --- Configuration ---
BG_COLOR = "#2E2E2E"  # Dark grey background
FG_COLOR = "#EAEAEA"  # Light grey/white text
ENTRY_BG = "#3C3C3C"
BUTTON_BG = "#555555"
BUTTON_FG = "#FFFFFF"
TREE_HEADING_BG = "#444444"
HIGHLIGHT_BG = "#0078D7" # A highlight color like VS Code blue

class StoreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Store Manager")
        self.root.geometry("950x650") # Adjusted size
        self.root.configure(bg=BG_COLOR)

        # --- Style Configuration ---
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam") # 'clam', 'alt', 'default', 'classic' - 'clam' often works well for coloring

        # General widget styling
        self.style.configure(".", background=BG_COLOR, foreground=FG_COLOR, fieldbackground=ENTRY_BG, borderwidth=1)
        self.style.map('.', background=[('active', BUTTON_BG)]) # General hover effect

        # Button style
        self.style.configure("TButton", background=BUTTON_BG, foreground=BUTTON_FG, padding=6, font=('Helvetica', 10))
        self.style.map("TButton", background=[('active', '#6A6A6A')]) # Darker hover for buttons

        # Entry style
        self.style.configure("TEntry", foreground=FG_COLOR, insertcolor=FG_COLOR, font=('Helvetica', 10)) # Set cursor color

        # Label style
        self.style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=('Helvetica', 10))
        self.style.configure("Title.TLabel", font=('Helvetica', 14, 'bold')) # Larger title labels

        # Treeview style
        self.style.configure("Treeview",
                             background=ENTRY_BG, # Background of the items area
                             foreground=FG_COLOR,
                             fieldbackground=ENTRY_BG, # Background when empty
                             rowheight=25,
                             font=('Helvetica', 10))
        self.style.configure("Treeview.Heading",
                             background=TREE_HEADING_BG,
                             foreground=FG_COLOR,
                             font=('Helvetica', 11, 'bold'),
                             padding=5)
        self.style.map("Treeview.Heading", background=[('active', '#5A5A5A')])
        # Treeview selection color
        self.style.map('Treeview',
                       background=[('selected', HIGHLIGHT_BG)],
                       foreground=[('selected', FG_COLOR)])

        # Frame style
        self.style.configure("TFrame", background=BG_COLOR)

        # --- Current Bill State ---
        self.current_bill_items = [] # List of tuples: (sku, name, price, quantity)
        self.current_bill_total = 0.0

        # --- Main Layout Frames ---
        # Control Frame (Top)
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Main Content Frame (holds products/billing and history side-by-side)
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Product/Billing Frame (Left/Center)
        self.product_frame = ttk.Frame(main_frame, padding="10")
        self.product_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Transaction History Frame (Right - initially might be narrow)
        self.history_frame = ttk.Frame(main_frame, padding="10")
        self.history_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5) # Fill vertically

        # Status Bar (Bottom)
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.set_status("Welcome!")

        # --- Control Frame Widgets ---
        ttk.Button(control_frame, text="List All Products", command=self.populate_product_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Add Product", command=self.show_add_product_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Remove Product", command=self.remove_selected_product).pack(side=tk.LEFT, padx=5)
        ttk.Separator(control_frame, orient='vertical').pack(side=tk.LEFT, fill='y', padx=15, pady=5)
        ttk.Button(control_frame, text="Start New Bill", command=self.start_billing_mode).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="View History", command=self.populate_transaction_history).pack(side=tk.LEFT, padx=5)


        # --- Product/Billing Frame Widgets ---
        ttk.Label(self.product_frame, text="Products / Current Bill", style="Title.TLabel").pack(pady=5, anchor='w')

        # Search/Add to Bill section (initially hidden, shown in billing mode)
        self.billing_actions_frame = ttk.Frame(self.product_frame)
        # Don't pack it yet

        ttk.Label(self.billing_actions_frame, text="Search Product (SKU/Name):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.billing_actions_frame, textvariable=self.search_var, width=25)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky='we')
        self.search_entry.bind("<Return>", self.search_and_display_products) # Allow searching with Enter key
        ttk.Button(self.billing_actions_frame, text="Search", command=self.search_and_display_products).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(self.billing_actions_frame, text="Quantity:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.qty_var = tk.StringVar(value="1") # Default quantity to 1
        self.qty_entry = ttk.Entry(self.billing_actions_frame, textvariable=self.qty_var, width=5)
        self.qty_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self.billing_actions_frame, text="Add to Bill", command=self.add_selected_to_bill).grid(row=1, column=2, padx=5, pady=5, sticky='w')

        # Treeview for displaying products or bill items
        self.product_tree = ttk.Treeview(self.product_frame, columns=("sku", "name", "price", "qty"), show="headings", selectmode="browse")
        self.product_tree.heading("sku", text="SKU")
        self.product_tree.heading("name", text="Name")
        self.product_tree.heading("price", text="Price")
        self.product_tree.heading("qty", text="Stock/Qty")
        self.product_tree.column("sku", width=100, anchor=tk.W)
        self.product_tree.column("name", width=250, anchor=tk.W)
        self.product_tree.column("price", width=80, anchor=tk.E)
        self.product_tree.column("qty", width=80, anchor=tk.E)
        self.product_tree.pack(pady=10, fill=tk.BOTH, expand=True)

        # --- Billing Summary & Actions (initially hidden) ---
        self.bill_summary_frame = ttk.Frame(self.product_frame)
        # Don't pack it yet

        self.bill_total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(self.bill_summary_frame, textvariable=self.bill_total_var, font=('Helvetica', 12, 'bold')).pack(side=tk.LEFT, padx=10)
        ttk.Button(self.bill_summary_frame, text="Checkout", command=self.process_checkout).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.bill_summary_frame, text="Cancel Bill", command=self.cancel_billing_mode).pack(side=tk.LEFT, padx=5)


        # --- Transaction History Frame Widgets ---
        ttk.Label(self.history_frame, text="History", style="Title.TLabel").pack(pady=5, anchor='w')
        self.history_tree = ttk.Treeview(self.history_frame, columns=("id", "time", "total"), show="headings", selectmode="browse")
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("time", text="Timestamp")
        self.history_tree.heading("total", text="Total")
        self.history_tree.column("id", width=50, anchor=tk.W)
        self.history_tree.column("time", width=150, anchor=tk.W)
        self.history_tree.column("total", width=80, anchor=tk.E)
        self.history_tree.pack(pady=10, fill=tk.BOTH, expand=True)
        self.history_tree.bind("<Double-1>", self.show_transaction_details) # Double-click to view details


        # --- Initial State ---
        self.populate_product_list() # Load products on startup
        self.populate_transaction_history() # Load history on startup

    # --- Helper Methods ---
    def set_status(self, message, error=False):
        self.status_var.set(message)
        if error:
            self.root.after(5000, lambda: self.status_var.set("")) # Clear error after 5s
        # Could add color change for errors later

    def clear_treeview(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    # --- Product List Methods ---
    def populate_product_list(self, products=None):
        """Populates the main treeview with product data."""
        self.clear_treeview(self.product_tree)
        self.product_tree.heading("qty", text="Stock") # Label as Stock
        try:
            if products is None:
                products = backend.get_all_products()
            for sku, name, price, quantity in products:
                self.product_tree.insert("", tk.END, values=(sku, name, f"{price:.2f}", quantity))
            if not products:
                 self.set_status("Inventory is empty.")
            else:
                 self.set_status(f"Displayed {len(products)} products.")
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not load products: {e}")
            self.set_status(f"Error loading products: {e}", error=True)

    # --- Add Product Methods ---
    def show_add_product_dialog(self):
        dialog = AddProductDialog(self.root, "Add New Product", self.style)
        if dialog.result:
            sku, name, price_str, qty_str = dialog.result
            try:
                # Basic validation (more could be added)
                price = float(price_str)
                quantity = int(qty_str)
                if not sku or not name: raise ValueError("SKU and Name are required.")
                if price < 0 or quantity < 0: raise ValueError("Price/Quantity cannot be negative.")

                # Call backend
                success_msg = backend.add_product(sku, name, price, quantity)
                messagebox.showinfo("Success", success_msg)
                self.populate_product_list() # Refresh the list
                self.set_status(success_msg)
            except ValueError as ve:
                messagebox.showerror("Input Error", str(ve))
                self.set_status(f"Add product failed: {ve}", error=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add product: {e}")
                self.set_status(f"Add product failed: {e}", error=True)

    # --- Remove Product Methods ---
    def remove_selected_product(self):
        selected_item = self.product_tree.focus() # Get selected item identifier
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a product from the list to remove.")
            return

        item_values = self.product_tree.item(selected_item, "values")
        sku_to_remove = item_values[0]
        product_name = item_values[1]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to remove '{product_name}' ({sku_to_remove})?"):
            try:
                success_msg = backend.remove_product(sku_to_remove)
                messagebox.showinfo("Success", success_msg)
                self.populate_product_list() # Refresh
                self.set_status(success_msg)
            except ValueError as ve: # Specific errors from backend
                messagebox.showerror("Removal Error", str(ve))
                self.set_status(f"Remove failed: {ve}", error=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove product: {e}")
                self.set_status(f"Remove failed: {e}", error=True)

    # --- Billing Methods ---
    def start_billing_mode(self):
        self.set_status("Billing mode active. Search and add items.")
        self.current_bill_items = []
        self.current_bill_total = 0.0
        self.update_bill_summary()

        # Configure product tree for billing (show items in bill)
        self.clear_treeview(self.product_tree)
        self.product_tree.heading("qty", text="Quantity") # Label as Qty for bill items
        # Add columns if they don't exist or reconfigure? For now, just reuse.

        # Show billing controls
        self.billing_actions_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        self.bill_summary_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # Maybe clear search initially?
        self.search_var.set("")
        self.qty_var.set("1")


    def cancel_billing_mode(self):
         if self.current_bill_items and not messagebox.askyesno("Cancel Bill", "Are you sure you want to cancel the current bill? Items will be lost."):
             return

         self.set_status("Billing cancelled. Displaying all products.")
         self.current_bill_items = []
         self.current_bill_total = 0.0

         # Hide billing controls
         self.billing_actions_frame.pack_forget()
         self.bill_summary_frame.pack_forget()

         # Restore product list view
         self.populate_product_list()


    def search_and_display_products(self, event=None): # event=None allows binding to <Return>
        search_term = self.search_var.get()
        if not search_term:
            messagebox.showinfo("Search", "Please enter a SKU or name to search.")
            return

        try:
            results = backend.find_products(search_term)
            self.clear_treeview(self.product_tree)
            self.product_tree.heading("qty", text="Stock") # Show Stock in search results
            if not results:
                 self.product_tree.insert("", tk.END, values=("", f"No products found matching '{search_term}'", "", ""))
                 self.set_status(f"No products found matching '{search_term}'.")
            else:
                 for sku, name, price, quantity in results:
                     self.product_tree.insert("", tk.END, values=(sku, name, f"{price:.2f}", quantity))
                 self.set_status(f"Found {len(results)} product(s). Select one to add.")
        except Exception as e:
            messagebox.showerror("Search Error", f"Error searching products: {e}")
            self.set_status(f"Search failed: {e}", error=True)


    def add_selected_to_bill(self):
        # This function should add the item currently selected in the *search results*
        # to the internal bill list, NOT modify the treeview directly yet.
        selected_item = self.product_tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please search and select a product from the list above to add.")
            return

        item_values = self.product_tree.item(selected_item, "values")
        if not item_values or not item_values[0]: # Check if it's a real product row
             messagebox.showwarning("Invalid Selection", "Please select a valid product row.")
             return

        sku, name, price_str, stock_str = item_values
        price = float(price_str)
        stock = int(stock_str)

        try:
            qty_to_add = int(self.qty_var.get())
            if qty_to_add <= 0:
                raise ValueError("Quantity must be positive.")
            if qty_to_add > stock:
                raise ValueError(f"Not enough stock for '{name}'. Only {stock} available.")

            # Check if item already in bill, if so, maybe update qty? For simplicity, just add.
            # A more robust approach would merge quantities.
            self.current_bill_items.append((sku, name, price, qty_to_add))
            self.current_bill_total += price * qty_to_add
            self.update_bill_summary()
            self.display_current_bill() # Update the treeview to show the bill
            self.set_status(f"Added {qty_to_add} x {name} to bill.")
            self.qty_var.set("1") # Reset quantity entry

        except ValueError as ve:
            messagebox.showerror("Input Error", str(ve))
            self.set_status(f"Add to bill failed: {ve}", error=True)


    def display_current_bill(self):
         """Updates the treeview to show items currently in the bill."""
         self.clear_treeview(self.product_tree)
         self.product_tree.heading("qty", text="Quantity") # Show Quantity being bought
         self.product_tree.heading("price", text="Unit Price")
         # Maybe add a 'Total Price' column? For simplicity, keeping it to 4 cols.

         temp_bill_summary = {} # Use dict to aggregate quantities for display
         for sku, name, price, qty in self.current_bill_items:
             if sku in temp_bill_summary:
                 temp_bill_summary[sku]['qty'] += qty
             else:
                 temp_bill_summary[sku] = {'name': name, 'price': price, 'qty': qty}

         for sku, item_data in temp_bill_summary.items():
              self.product_tree.insert("", tk.END, values=(sku, item_data['name'], f"{item_data['price']:.2f}", item_data['qty']))


    def update_bill_summary(self):
        self.bill_total_var.set(f"Total: ${self.current_bill_total:.2f}")


    def process_checkout(self):
        if not self.current_bill_items:
            messagebox.showwarning("Empty Bill", "Cannot checkout an empty bill.")
            return

        # Aggregate items before sending to backend (handles duplicates added separately)
        final_bill_items = []
        aggregated = {} # sku -> {'name': name, 'price': price, 'total_qty': qty}
        for sku, name, price, qty in self.current_bill_items:
             if sku not in aggregated:
                 aggregated[sku] = {'name': name, 'price': price, 'total_qty': 0}
             aggregated[sku]['total_qty'] += qty
             # Use the price from the *first* time the item was added in this bill
             # A real POS might handle price changes differently.

        for sku, data in aggregated.items():
             final_bill_items.append((sku, data['name'], data['price'], data['total_qty']))


        receipt_preview = "Checkout Confirmation:\n\n"
        for sku, name, price, qty in final_bill_items:
             receipt_preview += f"{qty} x {name} ({sku}) @ ${price:.2f} = ${qty*price:.2f}\n"
        receipt_preview += f"\nTOTAL: ${self.current_bill_total:.2f}"

        if messagebox.askyesno("Confirm Checkout", receipt_preview):
            try:
                transaction_id = backend.process_sale(final_bill_items)
                self.set_status(f"Checkout successful! Transaction ID: {transaction_id}")
                messagebox.showinfo("Sale Complete", f"Transaction {transaction_id} recorded.")
                # Offer to show receipt
                if messagebox.askyesno("View Receipt", "Do you want to view the receipt?"):
                    self.show_receipt_popup(transaction_id)

                # Exit billing mode and refresh background data
                self.cancel_billing_mode() # Resets state and shows product list
                self.populate_transaction_history() # Update history list

            except ValueError as ve: # Stock errors etc.
                messagebox.showerror("Checkout Error", str(ve))
                self.set_status(f"Checkout failed: {ve}", error=True)
                # Option: Refresh product list here to show updated stock if error was partial?
            except Exception as e:
                messagebox.showerror("Checkout Error", f"An unexpected error occurred: {e}")
                self.set_status(f"Checkout failed: {e}", error=True)


    # --- Transaction History Methods ---
    def populate_transaction_history(self):
        self.clear_treeview(self.history_tree)
        try:
            history = backend.get_transaction_history()
            for trans_id, timestamp, total in history:
                try:
                    # Attempt to format timestamp nicely
                    dt_object = datetime.datetime.fromisoformat(timestamp)
                    formatted_time = dt_object.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    formatted_time = timestamp[:16] # Fallback
                self.history_tree.insert("", tk.END, values=(trans_id, formatted_time, f"{total:.2f}"))
            # self.set_status("Transaction history loaded.") # Avoid overriding other statuses too quickly
        except Exception as e:
            messagebox.showerror("History Error", f"Could not load transaction history: {e}")
            self.set_status(f"Error loading history: {e}", error=True)

    def show_transaction_details(self, event): # Triggered by double-click
        selected_item = self.history_tree.focus()
        if not selected_item:
            return

        item_values = self.history_tree.item(selected_item, "values")
        transaction_id = int(item_values[0])
        self.show_receipt_popup(transaction_id)

    def show_receipt_popup(self, transaction_id):
        """Shows transaction details in a simple text popup."""
        try:
            trans_info, items = backend.get_transaction_details(transaction_id)
            tid, timestamp, total = trans_info
            try:
                dt_object = datetime.datetime.fromisoformat(timestamp)
                formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                formatted_time = timestamp

            receipt_text = f"--- RECEIPT ---\n"
            receipt_text += f"Transaction ID: {tid}\n"
            receipt_text += f"Date: {formatted_time}\n"
            receipt_text += "-" * 30 + "\n"
            receipt_text += f"{'Qty':<4} {'Item':<15} {'Price':>8}\n"
            receipt_text += "-" * 30 + "\n"
            calculated_total = 0
            for qty, name, sku, price in items:
                item_total = qty * price
                calculated_total += item_total
                receipt_text += f"{qty:<4} {name[:15]:<15} {item_total:>8.2f}\n" # Truncate name
            receipt_text += "-" * 30 + "\n"
            receipt_text += f"{'TOTAL:':<21} ${total:>8.2f}\n"
            receipt_text += "--- Thank You! ---"

            # Use a simple dialog or a Toplevel window with a Text widget
            ReceiptDialog(self.root, f"Receipt - ID: {transaction_id}", receipt_text, self.style)

        except Exception as e:
            messagebox.showerror("Receipt Error", f"Could not fetch details for transaction {transaction_id}: {e}")


# --- Custom Dialogs (Optional but cleaner) ---

class AddProductDialog(simpledialog.Dialog):
    def __init__(self, parent, title, style):
        self.style = style # Pass style for consistency
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        # Configure the dialog's background
        master.config(bg=BG_COLOR)

        ttk.Label(master, text="SKU:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.sku_entry = ttk.Entry(master, width=25)
        self.sku_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(master, text="Name:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.name_entry = ttk.Entry(master, width=25)
        self.name_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(master, text="Price:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.price_entry = ttk.Entry(master, width=25)
        self.price_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(master, text="Quantity:").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.qty_entry = ttk.Entry(master, width=25)
        self.qty_entry.grid(row=3, column=1, padx=5, pady=2)

        # Focus on first entry
        self.sku_entry.focus_set()
        return self.sku_entry # initial focus

    def buttonbox(self):
        # Override buttonbox to use ttk buttons if desired, or keep standard
        box = ttk.Frame(self)

        w = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()


    def apply(self):
        self.result = (self.sku_entry.get(),
                       self.name_entry.get(),
                       self.price_entry.get(),
                       self.qty_entry.get())

class ReceiptDialog(tk.Toplevel):
     def __init__(self, parent, title, text_content, style):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x450") # Adjust size as needed
        self.configure(bg=BG_COLOR)
        # Make it modal (optional)
        self.grab_set() # Prevent interaction with main window
        self.focus_set()
        self.transient(parent) # Keep it on top of parent

        # Use a Text widget for easy multi-line display and selection
        text_widget = tk.Text(self, wrap=tk.WORD, height=20, width=45,
                             bg=ENTRY_BG, fg=FG_COLOR,
                             font=("Courier", 10), # Monospaced font for alignment
                             borderwidth=0, highlightthickness=0) # Simple look
        text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, text_content)
        text_widget.config(state=tk.DISABLED) # Make it read-only

        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)

        self.wait_window(self) # Wait until this window is closed


# --- Main Execution ---
if __name__ == "__main__":
    # Ensure DB exists before starting GUI
    try:
        backend.init_db() # Safe to call even if DB exists
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to initialize or connect to database: {e}\nApplication will exit.")
        exit()

    root = tk.Tk()
    app = StoreApp(root)
    root.mainloop()