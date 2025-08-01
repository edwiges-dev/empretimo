import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, timedelta
import bcrypt

# Funções de segurança e banco de dados
def hash_senha(senha):
    # Gera um salt e faz o hash da senha
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha_fornecida, senha_hash):
    # Verifica se a senha fornecida corresponde ao hash
    return bcrypt.checkpw(senha_fornecida.encode('utf-8'), senha_hash.encode('utf-8'))

# Banco de dados
conn = sqlite3.connect('emprestimo_notebooks.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS usuarios (matricula TEXT PRIMARY KEY, nome TEXT, tipo TEXT, senha TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notebooks (patrimonio TEXT PRIMARY KEY, marca TEXT, modelo TEXT, status TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS emprestimos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patrimonio TEXT,
                matricula TEXT,
                responsavel TEXT,
                data_emprestimo TEXT,
                prazo_devolucao TEXT,
                data_devolucao TEXT,
                FOREIGN KEY (patrimonio) REFERENCES notebooks(patrimonio),
                FOREIGN KEY (matricula) REFERENCES usuarios(matricula),
                FOREIGN KEY (responsavel) REFERENCES usuarios(matricula))''')
c.execute('''CREATE TABLE IF NOT EXISTS logs_atividade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT,
                acao TEXT,
                data_hora TEXT)''')
conn.commit()

# Criar admin padrão se não existir (senha é '123')
c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'adm'")
if c.fetchone()[0] == 0:
    senha_admin_hash = hash_senha("123")
    try:
        c.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)", ("admin", "Administrador Padrão", "adm", senha_admin_hash))
        conn.commit()
        print("Administrador padrão criado: matrícula=admin, senha=123")
    except sqlite3.IntegrityError:
        pass

# Funções de banco de dados
def adicionar_usuario(matricula, nome, tipo, senha):
    try:
        senha_hash = hash_senha(senha)
        c.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)", (matricula, nome, tipo, senha_hash))
        conn.commit()
        return True, "Usuário adicionado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Erro: A matrícula já existe."

def adicionar_notebook(patrimonio, marca, modelo):
    try:
        c.execute("INSERT INTO notebooks VALUES (?, ?, ?, ?)", (patrimonio, marca, modelo, 'Disponível'))
        conn.commit()
        return True, "Notebook adicionado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Erro: O patrimônio já existe."

def atualizar_status_notebook(patrimonio, status):
    c.execute("UPDATE notebooks SET status = ? WHERE patrimonio = ?", (status, patrimonio))
    conn.commit()

def emprestar_notebook(patrimonio, aluno_matricula, responsavel_matricula, prazo):
    data_emprestimo = datetime.now()
    prazo_devolucao = data_emprestimo + timedelta(days=int(prazo))
    c.execute("INSERT INTO emprestimos (patrimonio, matricula, responsavel, data_emprestimo, prazo_devolucao, data_devolucao) VALUES (?, ?, ?, ?, ?, NULL)",
              (patrimonio, aluno_matricula, responsavel_matricula, data_emprestimo.strftime('%Y-%m-%d %H:%M:%S'), prazo_devolucao.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def devolver_notebook(patrimonio):
    data_devolucao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE emprestimos SET data_devolucao = ? WHERE patrimonio = ? AND data_devolucao IS NULL", (data_devolucao, patrimonio))
    conn.commit()

def buscar_emprestimos(filtro_texto='', filtro_tipo='todos'):
    if filtro_tipo == 'ativos':
        c.execute("SELECT * FROM emprestimos WHERE data_devolucao IS NULL AND (patrimonio LIKE ? OR matricula LIKE ? OR responsavel LIKE ?)", (f'%{filtro_texto}%', f'%{filtro_texto}%', f'%{filtro_texto}%'))
    else:
        if filtro_texto:
            c.execute("SELECT * FROM emprestimos WHERE patrimonio LIKE ? OR matricula LIKE ? OR responsavel LIKE ?", (f'%{filtro_texto}%', f'%{filtro_texto}%', f'%{filtro_texto}%'))
        else:
            c.execute("SELECT * FROM emprestimos")
    return c.fetchall()

def contar_emprestimos_atrasados():
    hoje = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("SELECT COUNT(*) FROM emprestimos WHERE data_devolucao IS NULL AND prazo_devolucao < ?", (hoje,))
    return c.fetchone()[0]

def registrar_log(usuario, acao):
    data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO logs_atividade (usuario, acao, data_hora) VALUES (?, ?, ?)", (usuario, acao, data_hora))
    conn.commit()

def exportar_csv():
    dados = buscar_emprestimos()
    if not dados:
        messagebox.showinfo("Sem dados", "Nenhum dado encontrado para exportar.")
        return
    arquivo = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV files", "*.csv"]])
    if arquivo:
        with open(arquivo, mode='w', newline='', encoding='utf-8') as f:
            escritor = csv.writer(f)
            escritor.writerow(['ID', 'Patrimônio', 'Matrícula Aluno', 'Responsável', 'Data Empréstimo', 'Prazo Devolução', 'Data Devolução'])
            escritor.writerows(dados)
        messagebox.showinfo("Exportado", "Relatório exportado com sucesso!")

# Interface
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Empréstimo de Notebooks")
        self.usuario_logado = None
        self.login_frame()

        self.root.protocol("WM_DELETE_WINDOW", self.fechar_app)
        
    def fechar_app(self):
        conn.close()
        self.root.destroy()

    def login_frame(self):
        for widget in self.root.winfo_children(): widget.destroy()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)
        ttk.Label(frame, text="Matrícula:").pack()
        self.matricula_entry = ttk.Entry(frame)
        self.matricula_entry.pack(pady=5)
        ttk.Label(frame, text="Senha:").pack()
        self.senha_entry = ttk.Entry(frame, show="*")
        self.senha_entry.pack(pady=5)
        ttk.Button(frame, text="Entrar", command=self.verificar_login).pack(pady=10)

    def verificar_login(self):
        matricula = self.matricula_entry.get()
        senha = self.senha_entry.get()
        c.execute("SELECT * FROM usuarios WHERE matricula = ?", (matricula,))
        usuario = c.fetchone()
        if usuario and verificar_senha(senha, usuario[3]):
            self.usuario_logado = usuario
            registrar_log(self.usuario_logado[0], f"Login realizado.")
            self.interface_principal()
            self.verificar_atrasos()
        else:
            messagebox.showerror("Erro de Login", "Matrícula ou senha incorreta.")
    
    def verificar_atrasos(self):
        atrasados = contar_emprestimos_atrasados()
        if atrasados > 0:
            messagebox.showwarning("Aviso de Atraso", f"⚠️ Existem {atrasados} empréstimo(s) atrasado(s)! Verifique a aba de busca ou inventário.")

    def interface_principal(self):
        for widget in self.root.winfo_children(): widget.destroy()
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.aba_emprestimo = ttk.Frame(notebook)
        self.aba_busca = ttk.Frame(notebook)
        
        notebook.add(self.aba_emprestimo, text="Empréstimo")
        notebook.add(self.aba_busca, text="Buscar")

        self.interface_emprestimo()
        self.interface_busca()
        
        if self.usuario_logado and self.usuario_logado[2] == 'adm':
            self.aba_inventario = ttk.Frame(notebook)
            self.aba_logs = ttk.Frame(notebook)
            notebook.add(self.aba_inventario, text="Inventário (ADM)")
            notebook.add(self.aba_logs, text="Logs (ADM)")
            self.interface_inventario_adm()
            self.interface_logs_adm()

    def interface_emprestimo(self):
        frame = self.aba_emprestimo
        if self.usuario_logado and self.usuario_logado[2] not in ('adm', 'professor'):
            ttk.Label(frame, text="Apenas administradores e professores podem realizar empréstimos.").pack(pady=20)
            return

        atrasados = contar_emprestimos_atrasados()
        if atrasados > 0:
            ttk.Label(frame, text=f"⚠️ {atrasados} empréstimo(s) atrasado(s)!", foreground="red", font=("Helvetica", 12, "bold")).pack(pady=5)

        ttk.Label(frame, text="Matrícula do Aluno:").pack()
        self.aluno_entry = ttk.Entry(frame)
        self.aluno_entry.pack()

        ttk.Label(frame, text="Patrimônio:").pack()
        self.pat_entrada = ttk.Entry(frame)
        self.pat_entrada.pack()

        ttk.Label(frame, text="Prazo (dias):").pack()
        self.prazo_entry = ttk.Entry(frame)
        self.prazo_entry.insert(0, "7")
        self.prazo_entry.pack()

        ttk.Button(frame, text="Emprestar", command=self.realizar_emprestimo).pack(pady=5)
        ttk.Button(frame, text="Devolver", command=self.realizar_devolucao).pack()

    def realizar_emprestimo(self):
        aluno_matricula = self.aluno_entry.get()
        patrimonio = self.pat_entrada.get()
        prazo = self.prazo_entry.get()

        if not aluno_matricula or not patrimonio or not prazo:
            messagebox.showerror("Erro", "Preencha todos os campos.")
            return

        try:
            prazo_dias = int(prazo)
        except ValueError:
            messagebox.showerror("Erro", "O prazo deve ser um número inteiro.")
            return

        c.execute("SELECT * FROM usuarios WHERE matricula = ?", (aluno_matricula,))
        if not c.fetchone():
            messagebox.showerror("Erro", "Aluno não cadastrado.")
            return

        c.execute("SELECT status FROM notebooks WHERE patrimonio = ?", (patrimonio,))
        notebook = c.fetchone()
        if not notebook:
            messagebox.showerror("Erro", "Notebook não cadastrado.")
            return
        if notebook[0] != 'Disponível':
            messagebox.showwarning("Aviso", f"Este notebook está {notebook[0]} e não pode ser emprestado.")
            return

        emprestar_notebook(patrimonio, aluno_matricula, self.usuario_logado[0], prazo_dias)
        atualizar_status_notebook(patrimonio, 'Emprestado')
        registrar_log(self.usuario_logado[0], f"Empréstimo do notebook {patrimonio} para {aluno_matricula}.")
        messagebox.showinfo("Sucesso", "Notebook emprestado.")
        self.aluno_entry.delete(0, tk.END)
        self.pat_entrada.delete(0, tk.END)
        self.prazo_entry.delete(0, tk.END)
        self.buscar_resultados()
        
    def realizar_devolucao(self):
        patrimonio = self.pat_entrada.get()
        if not patrimonio:
            messagebox.showerror("Erro", "Digite o patrimônio para a devolução.")
            return
        
        c.execute("SELECT * FROM emprestimos WHERE patrimonio = ? AND data_devolucao IS NULL", (patrimonio,))
        if not c.fetchone():
            messagebox.showerror("Erro", "Este notebook não está emprestado ou o patrimônio está incorreto.")
            return

        devolver_notebook(patrimonio)
        atualizar_status_notebook(patrimonio, 'Disponível')
        registrar_log(self.usuario_logado[0], f"Devolução do notebook {patrimonio}.")
        messagebox.showinfo("Sucesso", "Notebook devolvido.")
        self.pat_entrada.delete(0, tk.END)
        self.buscar_resultados()

    def interface_busca(self):
        frame = self.aba_busca
        ttk.Label(frame, text="Buscar por Patrimônio, Matrícula ou Responsável:").pack()
        self.busca_entry = ttk.Entry(frame)
        self.busca_entry.pack()
        self.filtro_var = tk.StringVar(value="ativos")
        ttk.Radiobutton(frame, text="Empréstimos Ativos", variable=self.filtro_var, value="ativos", command=self.buscar_resultados).pack(anchor='w')
        ttk.Radiobutton(frame, text="Todos os Empréstimos", variable=self.filtro_var, value="todos", command=self.buscar_resultados).pack(anchor='w')
        ttk.Button(frame, text="Buscar", command=self.buscar_resultados).pack()

        self.tabela = ttk.Treeview(frame, columns=("id", "patrimonio", "matricula", "responsavel", "data_emprestimo", "prazo", "devolucao"), show="headings")
        self.tabela.heading("id", text="ID")
        self.tabela.heading("patrimonio", text="Patrimônio")
        self.tabela.heading("matricula", text="Matrícula do Aluno")
        self.tabela.heading("responsavel", text="Responsável")
        self.tabela.heading("data_emprestimo", text="Data do Empréstimo")
        self.tabela.heading("prazo", text="Prazo de Devolução")
        self.tabela.heading("devolucao", text="Data da Devolução")
        self.tabela.pack(expand=True, fill="both")

        ttk.Button(frame, text="Exportar CSV", command=exportar_csv).pack(pady=10)
        self.buscar_resultados()
        
    def buscar_resultados(self):
        for row in self.tabela.get_children():
            self.tabela.delete(row)
        filtro_texto = self.busca_entry.get()
        filtro_tipo = self.filtro_var.get()
        resultados = buscar_emprestimos(filtro_texto, filtro_tipo)
        hoje = datetime.now()
        for r in resultados:
            tags = ()
            if r[6] is None:  # Se não foi devolvido
                try:
                    prazo = datetime.strptime(r[5], '%Y-%m-%d %H:%M:%S')
                    if hoje > prazo:
                        tags = ('atrasado',)
                except ValueError:
                    pass # Ignora se o formato da data estiver incorreto
            self.tabela.insert('', 'end', values=r, tags=tags)
        self.tabela.tag_configure('atrasado', background='red', foreground='white')

    def interface_inventario_adm(self):
        frame = self.aba_inventario
        
        notebook_cadastro_frame = ttk.Frame(frame, padding=10)
        notebook_cadastro_frame.pack(fill='x', padx=10, pady=5)

        # Cadastro de Notebook
        ttk.Label(notebook_cadastro_frame, text="Cadastrar Notebook:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(notebook_cadastro_frame, text="Patrimônio:").grid(row=1, column=0, sticky='w')
        self.novo_patrimonio = ttk.Entry(notebook_cadastro_frame)
        self.novo_patrimonio.grid(row=1, column=1, sticky='ew')
        ttk.Label(notebook_cadastro_frame, text="Marca:").grid(row=2, column=0, sticky='w')
        self.nova_marca = ttk.Entry(notebook_cadastro_frame)
        self.nova_marca.grid(row=2, column=1, sticky='ew')
        ttk.Label(notebook_cadastro_frame, text="Modelo:").grid(row=3, column=0, sticky='w')
        self.novo_modelo = ttk.Entry(notebook_cadastro_frame)
        self.novo_modelo.grid(row=3, column=1, sticky='ew')
        ttk.Button(notebook_cadastro_frame, text="Adicionar Notebook", command=self.adicionar_notebook_interface).grid(row=4, column=0, columnspan=2, pady=5)
        notebook_cadastro_frame.columnconfigure(1, weight=1)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        # Tabela de inventário de notebooks
        ttk.Label(frame, text="Inventário de Notebooks", font=("Helvetica", 10, "bold")).pack(pady=5)
        self.inventario_tabela = ttk.Treeview(frame, columns=("patrimonio", "marca", "modelo", "status"), show="headings")
        self.inventario_tabela.heading("patrimonio", text="Patrimônio")
        self.inventario_tabela.heading("marca", text="Marca")
        self.inventario_tabela.heading("modelo", text="Modelo")
        self.inventario_tabela.heading("status", text="Status")
        self.inventario_tabela.pack(expand=True, fill="both")
        self.inventario_tabela.bind('<<TreeviewSelect>>', self.exibir_historico_notebook)
        
        self.historico_frame = ttk.Frame(frame)
        self.historico_frame.pack(fill='x', pady=5)
        self.historico_label = ttk.Label(self.historico_frame, text="Histórico do Notebook:")
        self.historico_label.pack(anchor='w')
        self.tabela_historico = ttk.Treeview(self.historico_frame, columns=("data_emprestimo", "matricula", "data_devolucao"), show="headings")
        self.tabela_historico.heading("data_emprestimo", text="Empréstimo")
        self.tabela_historico.heading("matricula", text="Matrícula do Aluno")
        self.tabela_historico.heading("data_devolucao", text="Devolução")
        self.tabela_historico.pack(fill='both')

        self.atualizar_inventario()

    def interface_logs_adm(self):
        frame = self.aba_logs
        ttk.Label(frame, text="Logs de Atividade", font=("Helvetica", 14, "bold")).pack(pady=10)
        self.logs_tabela = ttk.Treeview(frame, columns=("data_hora", "usuario", "acao"), show="headings")
        self.logs_tabela.heading("data_hora", text="Data e Hora")
        self.logs_tabela.heading("usuario", text="Usuário")
        self.logs_tabela.heading("acao", text="Ação")
        self.logs_tabela.pack(expand=True, fill="both")
        self.atualizar_logs()
        
    def atualizar_inventario(self):
        for row in self.inventario_tabela.get_children():
            self.inventario_tabela.delete(row)
        
        c.execute("SELECT patrimonio, marca, modelo, status FROM notebooks")
        todos_notebooks = c.fetchall()
        
        for notebook in todos_notebooks:
            self.inventario_tabela.insert('', 'end', values=notebook)

    def exibir_historico_notebook(self, event):
        item_selecionado = self.inventario_tabela.focus()
        if not item_selecionado:
            return
        
        patrimonio = self.inventario_tabela.item(item_selecionado, 'values')[0]
        self.historico_label.config(text=f"Histórico do Notebook: {patrimonio}")

        for row in self.tabela_historico.get_children():
            self.tabela_historico.delete(row)

        c.execute("SELECT data_emprestimo, matricula, data_devolucao FROM emprestimos WHERE patrimonio = ? ORDER BY data_emprestimo DESC", (patrimonio,))
        historico = c.fetchall()
        
        for h in historico:
            self.tabela_historico.insert('', 'end', values=h)

    def atualizar_logs(self):
        for row in self.logs_tabela.get_children():
            self.logs_tabela.delete(row)
        
        c.execute("SELECT data_hora, usuario, acao FROM logs_atividade ORDER BY data_hora DESC")
        logs = c.fetchall()
        
        for log in logs:
            self.logs_tabela.insert('', 'end', values=log)

    def adicionar_usuario_interface(self):
        win = tk.Toplevel(self.root)
        win.title("Cadastrar Usuário")
        frame = ttk.Frame(win, padding=20)
        frame.pack(expand=True, fill='both')
        
        ttk.Label(frame, text="Matrícula:").pack()
        matricula_entry = ttk.Entry(frame)
        matricula_entry.pack()
        ttk.Label(frame, text="Nome:").pack()
        nome_entry = ttk.Entry(frame)
        nome_entry.pack()
        ttk.Label(frame, text="Tipo:").pack()
        tipo_var = tk.StringVar(value="aluno")
        tipo_combo = ttk.Combobox(frame, textvariable=tipo_var, values=["aluno", "professor", "adm"])
        tipo_combo.pack()
        ttk.Label(frame, text="Senha:").pack()
        senha_entry = ttk.Entry(frame, show="*")
        senha_entry.pack()

        def salvar():
            matricula = matricula_entry.get()
            nome = nome_entry.get()
            tipo = tipo_var.get()
            senha = senha_entry.get()
            if not matricula or not nome or not tipo or not senha:
                messagebox.showerror("Erro", "Todos os campos devem ser preenchidos.")
                return
            success, message = adicionar_usuario(matricula, nome, tipo, senha)
            if success:
                messagebox.showinfo("Sucesso", message)
                registrar_log(self.usuario_logado[0], f"Usuário {matricula} cadastrado.")
                win.destroy()
            else:
                messagebox.showerror("Erro", message)

        ttk.Button(frame, text="Salvar", command=salvar).pack(pady=10)

    def adicionar_notebook_interface(self):
        patrimonio = self.novo_patrimonio.get()
        marca = self.nova_marca.get()
        modelo = self.novo_modelo.get()

        if not patrimonio or not marca or not modelo:
            messagebox.showerror("Erro", "Todos os campos de notebook devem ser preenchidos.")
            return

        success, message = adicionar_notebook(patrimonio, marca, modelo)
        if success:
            messagebox.showinfo("Sucesso", message)
            registrar_log(self.usuario_logado[0], f"Notebook {patrimonio} cadastrado.")
            self.novo_patrimonio.delete(0, tk.END)
            self.nova_marca.delete(0, tk.END)
            self.novo_modelo.delete(0, tk.END)
            self.atualizar_inventario()
        else:
            messagebox.showerror("Erro", message)

# Inicia a aplicação
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()