import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import threading
import csv
import re

class M3U8DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("N_m3u8DL-RE 批量下载器")
        self.root.geometry("900x750")

        # 1. 单任务输入区
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(top_frame, text="单个链接:").grid(row=0, column=0, sticky="w")
        self.input_entry = tk.Entry(top_frame, width=60)
        self.input_entry.grid(row=0, column=1, padx=5)
        
        # 2. 批量任务区 (新添加)
        batch_frame = tk.LabelFrame(root, text="批量下载 (CSV 模式)")
        batch_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(batch_frame, text="选择 CSV 文件:").grid(row=0, column=0, padx=5, pady=5)
        self.csv_path_entry = tk.Entry(batch_frame, width=50)
        self.csv_path_entry.grid(row=0, column=1, padx=5)
        tk.Button(batch_frame, text="浏览...", command=self.browse_csv).grid(row=0, column=2, padx=5)
        tk.Label(batch_frame, text="* 格式: 第一列为链接, 第二列为文件名", fg="gray").grid(row=1, column=1, sticky="w")

        # --- 配置区 ---
        config_frame = tk.LabelFrame(root, text="设置")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(config_frame, text="保存目录:").grid(row=0, column=0)
        self.save_dir_entry = tk.Entry(config_frame, width=40)
        self.save_dir_entry.grid(row=0, column=1, padx=5)
        tk.Button(config_frame, text="选择目录", command=self.browse_dir).grid(row=0, column=2)
        
        tk.Label(config_frame, text="线程数:").grid(row=0, column=3, padx=10)
        self.threads_entry = tk.Entry(config_frame, width=5)
        self.threads_entry.insert(0, "16")
        self.threads_entry.grid(row=0, column=4)

        # --- 日志显示区 (核心修改点) ---
        log_label_frame = tk.LabelFrame(root, text="执行日志")
        log_label_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 1. 普通日志框 (正常滚动)
        self.log_area = scrolledtext.ScrolledText(
            log_label_frame, height=18, state="disabled", 
            font=("TkFixedFont", 9), bg="white", fg="black"
        )
        self.log_area.pack(fill="both", expand=True, padx=5, pady=2)

        # 2. 专用进度条框 (固定在底部，单行显示)
        self.progress_var = tk.StringVar(value="等待任务开始...")
        self.progress_bar_label = tk.Label(
            log_label_frame, textvariable=self.progress_var, 
            font=("TkFixedFont", 10, "bold"), bg="#f0f0f0", fg="#005fb8",
            anchor="w", relief="sunken", padx=10, pady=5
        )
        self.progress_bar_label.pack(fill="x", padx=5, pady=5)

        # --- 控制按钮 ---
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=10)
        self.start_btn = tk.Button(btn_frame, text="开始执行", bg="#28a745", fg="white", width=20, command=self.start_task)
        self.start_btn.pack(side="left")
        tk.Button(btn_frame, text="清空日志", command=self.clear_log).pack(side="right")

    def browse_csv(self):
        p = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if p: self.csv_path_entry.delete(0, tk.END); self.csv_path_entry.insert(0, p)

    def browse_dir(self):
        d = filedialog.askdirectory()
        if d: self.save_dir_entry.delete(0, tk.END); self.save_dir_entry.insert(0, d)

    def append_log(self, text):
        # 使用 strip() 去除首尾多余换行，再手动加上一个 \n 确保行间距紧凑
        clean_text = text.strip()
        if clean_text:
            self.log_area.config(state="normal")
            self.log_area.insert(tk.END, clean_text + "\n")
            self.log_area.see(tk.END)
            self.log_area.config(state="disabled")

    def update_progress(self, text):
        # 实时更新底部固定的进度行
        self.progress_var.set(text.strip())

    def clear_log(self):
        self.log_area.config(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state="disabled")
        self.progress_var.set("等待任务开始...")

    def start_task(self):
        csv_p = self.csv_path_entry.get().strip()
        url = self.input_entry.get().strip()
        tasks = []
        
        if csv_p:
            try:
                with open(csv_p, 'r', encoding='utf-8-sig') as f:
                    for row in csv.reader(f):
                        if len(row) >= 2: tasks.append({"url": row[0], "name": row[1]})
            except Exception as e: messagebox.showerror("Error", str(e)); return
        elif url:
            tasks.append({"url": url, "name": ""})
        else:
            messagebox.showwarning("提示", "请提供链接或CSV"); return

        self.start_btn.config(state="disabled")
        threading.Thread(target=self.run_process, args=(tasks,), daemon=True).start()

    def run_process(self, tasks):
        # 匹配进度条的正则，涵盖百分比、速率和剩余时间 [cite: 6, 23]
        progress_re = re.compile(r'(Vid|Aud|Kbps|%|--:--:--|Mbps)')
        
        for i, t in enumerate(tasks):
            # 基础命令参数 [cite: 1, 6, 7, 8]
            cmd = ["N_m3u8DL-RE", f'"{t["url"]}"', "--no-ansi-color", "--force-ansi-console", "--auto-select"]
            if self.save_dir_entry.get(): 
                cmd.extend(["--save-dir", f'"{self.save_dir_entry.get()}"']) # 设置输出目录 [cite: 2]
            if t["name"]: 
                cmd.extend(["--save-name", f'"{t["name"]}"']) # 设置保存文件名 [cite: 2]
            if self.threads_entry.get(): 
                cmd.extend(["--thread-count", self.threads_entry.get()]) # 设置下载线程数 [cite: 6]
            
            full_cmd = " ".join(cmd)
            self.root.after(0, self.append_log, f">>> 任务 {i+1}/{len(tasks)} 开始")
            
            proc = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   shell=True, text=True, encoding='gbk', errors='ignore')
            
            for line in proc.stdout:
                # 针对某些行可能只包含空白字符的情况进行过滤
                if not line.strip():
                    continue

                if progress_re.search(line):
                    # 处理进度条信息：只取最后一段并更新底部状态栏 [cite: 23]
                    p_text = line.split("\r")[-1] if "\r" in line else line
                    self.root.after(0, self.update_progress, p_text)
                else:
                    # 处理普通日志：如“读取媒体信息”、“合并中”等 [cite: 8, 11]
                    self.root.after(0, self.append_log, line)
            proc.wait()
            
        self.root.after(0, self.append_log, "\n[所有下载已完成]\n")
        self.root.after(0, lambda: self.start_btn.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    M3U8DownloaderGUI(root)
    root.mainloop()