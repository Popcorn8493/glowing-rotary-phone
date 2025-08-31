from tkinter import Button, END, Frame, Label, Listbox, Scrollbar, Tk
from tkinter.filedialog import askopenfilename


def create_modern_gui():
    root = Tk()
    root.title("MTG Card Matcher - Batch Confirmation")
    root.configure(bg='#2b2b2b')
    style_config = {
        'bg': '#2b2b2b',
        'fg': '#ffffff',
        'font': ('Segoe UI', 11),
        'selectbackground': '#404040',
        'selectforeground': '#ffffff'
    }
    window_width = 1200
    window_height = 700
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    return root, style_config


def confirm_match_simple_fallback(pending_items):
    results = {}
    print("\nGUI unavailable, using console confirmation:")
    print("Commands: [1-9] select match, [s] skip, [a] auto-confirm all remaining")
    
    for i, (normalized_key, matches, ref_data) in enumerate(pending_items):
        print(f"\n--- Item {i + 1}/{len(pending_items)} ---")
        print(f"Card: {normalized_key[0]}")
        print(f"Set: {normalized_key[1]} | Number: {normalized_key[2]}")
        
        for idx, (match, score) in enumerate(matches[:5]):
            candidate = ref_data.get(match, {})
            print(f"{idx + 1}: {candidate.get('Product Name', 'Unknown')} (Score: {score})")
        
        while True:
            try:
                choice = input("Select [1-5], [s]kip, [a]uto-all: ").strip().lower()
                if choice == 's':
                    results[i] = None
                    break
                elif choice == 'a':
                    for j in range(i, len(pending_items)):
                        _, m, _ = pending_items[j]
                        results[j] = m[0][0] if m else None
                    return results
                elif choice.isdigit() and 1 <= int(choice) <= min(5, len(matches)):
                    results[i] = matches[int(choice) - 1][0]
                    break
                else:
                    print("Invalid choice. Try again.")
            except (ValueError, IndexError):
                print("Invalid choice. Try again.")
    
    return results


def confirm_match_gui_batch(pending_items):
    if not pending_items:
        return {}
    
    print(f"Opening batch confirmation GUI for {len(pending_items)} items...")
    
    try:
        root, style = create_modern_gui()
        root.lift()
        root.focus_force()
        root.attributes('-topmost', True)
        root.after(100, lambda: root.attributes('-topmost', False))
        
        results = {}
        current_item = [0]
    except Exception as e:
        print(f"GUI initialization failed: {e}")
        return confirm_match_simple_fallback(pending_items)
    
    header_frame = Frame(root, bg=style['bg'], height=60)
    header_frame.pack(fill="x", padx=20, pady=10)
    header_frame.pack_propagate(False)
    
    title_label = Label(header_frame,
                        text=f"Card Matching Confirmation ({len(pending_items)} items)",
                        font=('Segoe UI', 16, 'bold'),
                        bg=style['bg'], fg='#4CAF50')
    title_label.pack(side="top", pady=5)
    
    progress_label = Label(header_frame,
                           text="",
                           font=('Segoe UI', 10),
                           bg=style['bg'], fg='#cccccc')
    progress_label.pack(side="top")
    
    main_frame = Frame(root, bg=style['bg'])
    main_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    left_frame = Frame(main_frame, bg=style['bg'], width=400)
    left_frame.pack(side="left", fill="y", padx=(0, 10))
    left_frame.pack_propagate(False)
    
    right_frame = Frame(main_frame, bg=style['bg'])
    right_frame.pack(side="right", fill="both", expand=True)
    
    card_info_label = Label(left_frame,
                            text="",
                            font=('Segoe UI', 12, 'bold'),
                            bg=style['bg'], fg='#ffffff',
                            wraplength=380, justify="left")
    card_info_label.pack(pady=10)
    
    matches_label = Label(left_frame,
                          text="Available Matches:",
                          font=('Segoe UI', 11, 'bold'),
                          bg=style['bg'], fg='#4CAF50')
    matches_label.pack(pady=(20, 5))
    
    matches_listbox = Listbox(left_frame,
                              height=15,
                              font=('Segoe UI', 10),
                              bg=style['bg'], fg=style['fg'],
                              selectbackground=style['selectbackground'],
                              selectforeground=style['selectforeground'],
                              activestyle='none')
    matches_listbox.pack(fill="both", expand=True)
    
    matches_scrollbar = Scrollbar(left_frame, orient="vertical", command=matches_listbox.yview)
    matches_scrollbar.pack(side="right", fill="y")
    matches_listbox.configure(yscrollcommand=matches_scrollbar.set)
    
    button_frame = Frame(left_frame, bg=style['bg'])
    button_frame.pack(fill="x", pady=20)
    
    confirm_button = Button(button_frame,
                            text="Confirm Selection",
                            font=('Segoe UI', 10, 'bold'),
                            bg='#4CAF50', fg='white',
                            activebackground='#45a049',
                            activeforeground='white',
                            relief="flat",
                            padx=20, pady=8)
    confirm_button.pack(side="left", padx=(0, 10))
    
    skip_button = Button(button_frame,
                         text="Skip This Card",
                         font=('Segoe UI', 10),
                         bg='#f44336', fg='white',
                         activebackground='#da190b',
                         activeforeground='white',
                         relief="flat",
                         padx=20, pady=8)
    skip_button.pack(side="left", padx=(0, 10))
    
    auto_all_button = Button(button_frame,
                             text="Auto-Confirm All",
                             font=('Segoe UI', 10),
                             bg='#2196F3', fg='white',
                             activebackground='#0b7dda',
                             activeforeground='white',
                             relief="flat",
                             padx=20, pady=8)
    auto_all_button.pack(side="left")
    
    preview_frame = Frame(right_frame, bg=style['bg'])
    preview_frame.pack(fill="both", expand=True)
    
    preview_label = Label(preview_frame,
                          text="Match Preview",
                          font=('Segoe UI', 12, 'bold'),
                          bg=style['bg'], fg='#4CAF50')
    preview_label.pack(pady=(0, 10))
    
    preview_text = Label(preview_frame,
                         text="",
                         font=('Segoe UI', 10),
                         bg=style['bg'], fg='#cccccc',
                         wraplength=600, justify="left",
                         anchor="nw")
    preview_text.pack(fill="both", expand=True, pady=10)
    
    def update_display():
        if current_item[0] >= len(pending_items):
            root.quit()
            return
        
        normalized_key, matches, ref_data = pending_items[current_item[0]]
        
        progress_label.config(text=f"Item {current_item[0] + 1} of {len(pending_items)}")
        
        card_info = f"Card: {normalized_key[0]}\n"
        card_info += f"Set: {normalized_key[1]}\n"
        card_info += f"Number: {normalized_key[2] or 'N/A'}\n"
        card_info += f"Condition: {normalized_key[3]}"
        card_info_label.config(text=card_info)
        
        matches_listbox.delete(0, END)
        for idx, (match, score) in enumerate(matches[:10]):
            candidate = ref_data.get(match, {})
            display_text = f"{idx + 1}. {candidate.get('Product Name', 'Unknown')}"
            if score:
                display_text += f" (Score: {score})"
            matches_listbox.insert(END, display_text)
        
        if matches_listbox.size() > 0:
            matches_listbox.selection_set(0)
            update_preview()
    
    def update_preview():
        selection = matches_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(pending_items[current_item[0]][1]):
                match, score = pending_items[current_item[0]][1][idx]
                candidate = pending_items[current_item[0]][2].get(match, {})
                
                preview = f"Product Name: {candidate.get('Product Name', 'Unknown')}\n"
                preview += f"Set Name: {candidate.get('Set Name', 'Unknown')}\n"
                preview += f"Number: {candidate.get('Number', 'Unknown')}\n"
                preview += f"Rarity: {candidate.get('Rarity', 'Unknown')}\n"
                preview += f"Condition: {candidate.get('Condition', 'Unknown')}\n"
                preview += f"TCGplayer ID: {candidate.get('TCGplayer Id', 'Unknown')}\n"
                if score:
                    preview += f"Match Score: {score}"
                
                preview_text.config(text=preview)
    
    def on_confirm():
        selection = matches_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(pending_items[current_item[0]][1]):
                results[current_item[0]] = pending_items[current_item[0]][1][idx][0]
                current_item[0] += 1
                update_display()
    
    def on_skip():
        results[current_item[0]] = None
        current_item[0] += 1
        update_display()
    
    def on_auto_all():
        for i in range(current_item[0], len(pending_items)):
            _, matches, _ = pending_items[i]
            results[i] = matches[0][0] if matches else None
        root.quit()
    
    def on_listbox_select(event):
        update_preview()
    
    confirm_button.config(command=on_confirm)
    skip_button.config(command=on_skip)
    auto_all_button.config(command=on_auto_all)
    matches_listbox.bind('<<ListboxSelect>>', on_listbox_select)
    
    update_display()
    
    try:
        root.mainloop()
    except Exception as e:
        print(f"GUI error: {e}")
        return confirm_match_simple_fallback(pending_items)
    
    return results


def select_csv_file(prompt):
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    filename = askopenfilename(
        title=prompt,
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    root.destroy()
    return filename
