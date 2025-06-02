import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, timedelta

# Banco de dados
conn = sqlite3.connect('emprestimo_notebooks.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS usuarios (matricula TEXT PRIMARY KEY, nome TEXT, tipo TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notebooks (patrimonio TEXT PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS emprestimos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patrimonio TEXT,
                matricula TEXT,
                data_emprestimo TEXT,
                prazo_devolucao TEXT,
                data_devolucao TEXT,
                FOREIGN KEY (patrimonio) REFERENCES notebooks(patrimonio),
                FOREIGN KEY (matricula) REFERENCES usuarios(matricula))''')
conn.commit()

# Funções de banco de dados
def adicionar_usuario(matricula, nome, tipo):
    try:
        c.execute("INSERT INTO usuarios VALUES (?, ?, ?)", (matricula, nome, tipo))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def adicionar_notebook(patrimonio):
    try:
        c.execute("INSERT INTO notebooks VALUES (?)", (patrimonio,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def emprestar_notebook(patrimonio, matricula, prazo):
    data_emprestimo = datetime.now()
    prazo_devolucao = data_emprestimo + timedelta(days=int(prazo))
    c.execute("INSERT INTO emprestimos (patrimonio, matricula, data_emprestimo, prazo_devolucao, data_devolucao) VALUES (?, ?, ?, ?, NULL)",
              (patrimonio, matricula, data_emprestimo.strftime('%Y-%m-%d %H:%M:%S'), prazo_devolucao.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def devolver_notebook(patrimonio):
    data_devolucao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE emprestimos SET data_devolucao = ? WHERE patrimonio = ? AND data_devolucao IS NULL", (data_devolucao, patrimonio))
    conn.commit()

def buscar_emprestimos(filtro=''):
    if filtro:
        c.execute("SELECT * FROM emprestimos WHERE patrimonio LIKE ? OR matricula LIKE ?", (f'%{filtro}%', f'%{filtro}%'))
    else:
        c.execute("SELECT * FROM emprestimos")
    return c.fetchall()

def exportar_csv():
    dados = buscar_emprestimos()
    if not dados:
        messagebox.showinfo("Sem dados", "Nenhum dado encontrado para exportar.")
        return
    arquivo = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV files", "*.csv"]])
    if arquivo:
        with open(arquivo, mode='w', newline='', encoding='utf-8') as f:
            escritor = csv.writer(f)
            escritor.writerow(['ID', 'Patrimônio', 'Matrícula', 'Data Empréstimo', 'Prazo Devolução', 'Data Devolução'])
            escritor.writerows(dados)
        messagebox.showinfo("Exportado", "Relatório exportado com sucesso!")

# Interface
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Empréstimo de Notebooks")

        self.usuario_logado = None

        self.login_frame()

    def login_frame(self):
        for widget in self.root.winfo_children(): widget.destroy()

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        ttk.Label(frame, text="Matrícula:").pack()
        self.matricula_entry = ttk.Entry(frame)
        self.matricula_entry.pack()

        ttk.Button(frame, text="Entrar", command=self.verificar_login).pack(pady=10)

    def verificar_login(self):
        matricula = self.matricula_entry.get()
        c.execute("SELECT * FROM usuarios WHERE matricula = ?", (matricula,))
        usuario = c.fetchone()
        if usuario:
            self.usuario_logado = usuario
            self.interface_principal()
        else:
            resposta = messagebox.askyesno("Matrícula não encontrada", "Matrícula não encontrada. Deseja cadastrá-la agora?")
            if resposta:
                self.interface_admin()

    def interface_principal(self):
        for widget in self.root.winfo_children(): widget.destroy()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.aba_emprestimo = ttk.Frame(notebook)
        self.aba_busca = ttk.Frame(notebook)
        self.aba_admin = ttk.Frame(notebook)

        notebook.add(self.aba_emprestimo, text="Empréstimo")
        notebook.add(self.aba_busca, text="Buscar")
        notebook.add(self.aba_admin, text="Admin")

        self.interface_emprestimo()
        self.interface_busca()
        self.interface_admin()

    def interface_emprestimo(self):
        frame = self.aba_emprestimo

        ttk.Label(frame, text="Patrimônio:").pack()
        self.pat_entrada = ttk.Entry(frame)
        self.pat_entrada.pack()

        ttk.Label(frame, text="Prazo (dias):").pack()
        self.prazo_entrada = ttk.Entry(frame)
        self.prazo_entrada.insert(0, "7")
        self.prazo_entrada.pack()

        ttk.Button(frame, text="Emprestar", command=self.realizar_emprestimo).pack(pady=5)
        ttk.Button(frame, text="Devolver", command=self.realizar_devolucao).pack()

    def realizar_emprestimo(self):
        if self.usuario_logado[2] not in ('professor', 'adm'):
            messagebox.showerror("Permissão negada", "Somente administradores ou professores podem emprestar notebooks.")
            return

        patrimonio = self.pat_entrada.get()
        prazo = self.prazo_entrada.get()
        if not patrimonio or not prazo:
            messagebox.showerror("Erro", "Preencha todos os campos.")
            return
        c.execute("SELECT * FROM notebooks WHERE patrimonio = ?", (patrimonio,))
        if not c.fetchone():
            messagebox.showerror("Erro", "Notebook não cadastrado.")
            return
        c.execute("SELECT * FROM emprestimos WHERE patrimonio = ? AND data_devolucao IS NULL", (patrimonio,))
        if c.fetchone():
            messagebox.showwarning("Aviso", "Este notebook já está emprestado.")
            return
        emprestar_notebook(patrimonio, self.usuario_logado[0], prazo)
        messagebox.showinfo("Sucesso", "Notebook emprestado.")

    def realizar_devolucao(self):
        patrimonio = self.pat_entrada.get()
        if not patrimonio:
            messagebox.showerror("Erro", "Digite o patrimônio.")
            return
        devolver_notebook(patrimonio)
        messagebox.showinfo("Sucesso", "Notebook devolvido.")

    def interface_busca(self):
        frame = self.aba_busca

        ttk.Label(frame, text="Buscar por Patrimônio ou Matrícula:").pack()
        self.busca_entry = ttk.Entry(frame)
        self.busca_entry.pack()

        ttk.Button(frame, text="Buscar", command=self.buscar_resultados).pack()

        self.tabela = ttk.Treeview(frame, columns=("id", "patrimonio", "matricula", "data_emprestimo", "prazo", "devolucao"), show="headings")
        for col in self.tabela["columns"]:
            self.tabela.heading(col, text=col.capitalize())
        self.tabela.pack(expand=True, fill="both")

        ttk.Button(frame, text="Exportar CSV", command=exportar_csv).pack(pady=10)

    def buscar_resultados(self):
        for row in self.tabela.get_children():
            self.tabela.delete(row)
        resultados = buscar_emprestimos(self.busca_entry.get())
        for r in resultados:
            self.tabela.insert('', 'end', values=r)

    def interface_admin(self):
        for widget in self.root.winfo_children(): widget.destroy()

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Nova matrícula:").pack()
        self.nova_matricula = ttk.Entry(frame)
        self.nova_matricula.pack()

        ttk.Label(frame, text="Nome:").pack()
        self.nome_entry = ttk.Entry(frame)
        self.nome_entry.pack()

        ttk.Label(frame, text="Tipo (aluno/professor/adm):").pack()
        self.tipo_entry = ttk.Entry(frame)
        self.tipo_entry.pack()

        ttk.Button(frame, text="Adicionar Usuário", command=self.adicionar_usuario_interface).pack(pady=5)

        ttk.Label(frame, text="Novo patrimônio:").pack()
        self.novo_patrimonio = ttk.Entry(frame)
        self.novo_patrimonio.pack()
        ttk.Button(frame, text="Adicionar Notebook", command=self.adicionar_notebook_interface).pack()

        ttk.Button(frame, text="Voltar", command=self.login_frame).pack(pady=10)

    def adicionar_usuario_interface(self):
        adicionar_usuario(self.nova_matricula.get(), self.nome_entry.get(), self.tipo_entry.get())
        messagebox.showinfo("Sucesso", "Usuário cadastrado.")

    def adicionar_notebook_interface(self):
        adicionar_notebook(self.novo_patrimonio.get())
        messagebox.showinfo("Sucesso", "Notebook cadastrado.")

root = tk.Tk()
App(root)
root.mainloop()
