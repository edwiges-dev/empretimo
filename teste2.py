import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, timedelta
import bcrypt
from ttkthemes import ThemedTk

# Funções de segurança e banco de dados
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha_fornecida, senha_hash):
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
        
def editar_usuario_db(matricula, novo_nome, novo_tipo):
    try:
        c.execute("UPDATE usuarios SET nome = ?, tipo = ? WHERE matricula = ?", (novo_nome, novo_tipo, matricula))
        conn.commit()
        return True, "Usuário editado com sucesso."
    except sqlite3.Error as e:
        return False, f"Erro ao editar usuário: {e}"

def adicionar_notebook(patrimonio, marca, modelo):
    try:
        c.execute("INSERT INTO notebooks VALUES (?, ?, ?, ?)", (patrimonio, marca, modelo, 'Disponível'))
        conn.commit()
        return True, "Notebook adicionado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Erro: O patrimônio já existe."

def editar_notebook_db(patrimonio, nova_marca, novo_modelo, novo_status):
    try:
        c.execute("UPDATE notebooks SET marca = ?, modelo = ?, status = ? WHERE patrimonio = ?", (nova_marca, novo_modelo, novo_status, patrimonio))
        conn.commit()
        return True, "Notebook editado com sucesso."
    except sqlite3.Error as e:
        return False, f"Erro ao editar notebook: {e}"

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
        frame = ttk.Frame(self.root, padding=40)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Acesso ao Sistema", font=('Helvetica', 16, 'bold')).pack(pady=20)
        
        ttk.Label(frame, text="Matrícula:", font=('Helvetica', 12)).pack(anchor='w', pady=(0, 5))
        self.matricula_entry = ttk.Entry(frame, font=('Helvetica', 12))
        self.matricula_entry.pack(fill='x', pady=(0, 15))
        
        ttk.Label(frame, text="Senha:", font=('Helvetica', 12)).pack(anchor='w', pady=(0, 5))
        self.senha_entry = ttk.Entry(frame, show="*", font=('Helvetica', 12))
        self.senha_entry.pack(fill='x', pady=(0, 15))
        
        ttk.Button(frame, text="Entrar", command=self.verificar_login).pack(pady=10, fill='x')

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
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.aba_emprestimo = ttk.Frame(notebook)
        self.aba_busca = ttk.Frame(notebook)
        
        notebook.add(self.aba_emprestimo, text="Empréstimo")
        notebook.add(self.aba_busca, text="Buscar")

        self.interface_emprestimo()
        self.interface_busca()
        
        if self.usuario_logado and self.usuario_logado[2] == 'adm':
            self.aba_inventario = ttk.Frame(notebook)
            self.aba_usuarios = ttk.Frame(notebook)
            self.aba_logs = ttk.Frame(notebook)
            notebook.add(self.aba_inventario, text="Inventário (ADM)")
            notebook.add(self.aba_usuarios, text="Usuários (ADM)")
            notebook.add(self.aba_logs, text="Logs (ADM)")
            self.interface_inventario_adm()
            self.interface_usuarios_adm()
            self.interface_logs_adm()

    def interface_emprestimo(self):
        frame = ttk.Frame(self.aba_emprestimo, padding=20)
        frame.pack(expand=True, fill='both')

        if self.usuario_logado and self.usuario_logado[2] not in ('adm', 'professor'):
            ttk.Label(frame, text="Apenas administradores e professores podem realizar empréstimos.", font=('Helvetica', 12, 'bold')).pack(pady=40)
            return

        atrasados = contar_emprestimos_atrasados()
        if atrasados > 0:
            ttk.Label(frame, text=f"⚠️ {atrasados} empréstimo(s) atrasado(s)!", foreground="red", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Matrícula do Aluno:", font=('Helvetica', 10)).grid(row=0, column=0, sticky='w', pady=(5,0))
        self.aluno_entry = ttk.Entry(input_frame)
        self.aluno_entry.grid(row=0, column=1, padx=10, pady=(5,0), sticky='ew')

        ttk.Label(input_frame, text="Patrimônio:", font=('Helvetica', 10)).grid(row=1, column=0, sticky='w', pady=(5,0))
        self.pat_entrada = ttk.Entry(input_frame)
        self.pat_entrada.grid(row=1, column=1, padx=10, pady=(5,0), sticky='ew')

        ttk.Label(input_frame, text="Prazo (dias):", font=('Helvetica', 10)).grid(row=2, column=0, sticky='w', pady=(5,0))
        self.prazo_entry = ttk.Entry(input_frame)
        self.prazo_entry.insert(0, "7")
        self.prazo_entry.grid(row=2, column=1, padx=10, pady=(5,0), sticky='ew')

        input_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10, fill='x')
        ttk.Button(btn_frame, text="Emprestar", command=self.realizar_emprestimo).pack(side='left', expand=True, padx=5)
        ttk.Button(btn_frame, text="Devolver", command=self.realizar_devolucao).pack(side='left', expand=True, padx=5)

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
        self.atualizar_inventario()
        
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
        self.atualizar_inventario()

    def interface_busca(self):
        frame = ttk.Frame(self.aba_busca, padding=20)
        frame.pack(expand=True, fill='both')
        
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Buscar por Patrimônio, Matrícula ou Responsável:", font=('Helvetica', 10)).pack(anchor='w', pady=(5, 0))
        self.busca_entry = ttk.Entry(search_frame)
        self.busca_entry.pack(fill='x', pady=(0, 10))
        
        filtro_frame = ttk.Frame(search_frame)
        filtro_frame.pack(fill='x', pady=(0, 10))
        
        self.filtro_var = tk.StringVar(value="ativos")
        ttk.Radiobutton(filtro_frame, text="Empréstimos Ativos", variable=self.filtro_var, value="ativos", command=self.buscar_resultados).pack(side='left', padx=5)
        ttk.Radiobutton(filtro_frame, text="Todos os Empréstimos", variable=self.filtro_var, value="todos", command=self.buscar_resultados).pack(side='left', padx=5)
        ttk.Button(filtro_frame, text="Buscar", command=self.buscar_resultados).pack(side='right', padx=5)

        self.tabela = ttk.Treeview(frame, columns=("id", "patrimonio", "matricula", "responsavel", "data_emprestimo", "prazo", "devolucao"), show="headings")
        self.tabela.heading("id", text="ID")
        self.tabela.heading("patrimonio", text="Patrimônio")
        self.tabela.heading("matricula", text="Matrícula do Aluno")
        self.tabela.heading("responsavel", text="Responsável")
        self.tabela.heading("data_emprestimo", text="Data do Empréstimo")
        self.tabela.heading("prazo", text="Prazo de Devolução")
        self.tabela.heading("devolucao", text="Data da Devolução")
        self.tabela.pack(expand=True, fill="both")

        ttk.Button(frame, text="Exportar CSV", command=exportar_csv).pack(pady=10, side='right')
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
            if r[6] is None:
                try:
                    prazo = datetime.strptime(r[5], '%Y-%m-%d %H:%M:%S')
                    if hoje > prazo:
                        tags = ('atrasado',)
                except ValueError:
                    pass
            self.tabela.insert('', 'end', values=r, tags=tags)
        self.tabela.tag_configure('atrasado', background='red', foreground='white')

    def interface_inventario_adm(self):
        frame = ttk.Frame(self.aba_inventario, padding=20)
        frame.pack(expand=True, fill='both')
        
        cadastro_frame = ttk.LabelFrame(frame, text="Gerenciamento de Notebooks", padding=10)
        cadastro_frame.pack(fill='x', pady=10)
        
        cadastro_frame.columnconfigure(0, weight=1)
        cadastro_frame.columnconfigure(1, weight=1)
        cadastro_frame.columnconfigure(2, weight=1)
        
        ttk.Button(cadastro_frame, text="Cadastrar Notebook", command=self.adicionar_notebook_interface).grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(cadastro_frame, text="Alterar Status", command=self.alterar_status_notebook_interface).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(cadastro_frame, text="Editar Notebook", command=self.editar_notebook_interface).grid(row=0, column=2, padx=5, pady=5, sticky='ew')

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=20)

        inventario_frame = ttk.LabelFrame(frame, text="Inventário de Notebooks", padding=10)
        inventario_frame.pack(expand=True, fill='both')
        
        self.inventario_tabela = ttk.Treeview(inventario_frame, columns=("patrimonio", "marca", "modelo", "status"), show="headings")
        self.inventario_tabela.heading("patrimonio", text="Patrimônio")
        self.inventario_tabela.heading("marca", text="Marca")
        self.inventario_tabela.heading("modelo", text="Modelo")
        self.inventario_tabela.heading("status", text="Status")
        self.inventario_tabela.pack(expand=True, fill="both")
        self.inventario_tabela.bind('<<TreeviewSelect>>', self.exibir_historico_notebook)
        
        historico_frame = ttk.LabelFrame(frame, text="Histórico de Empréstimos do Item", padding=10)
        historico_frame.pack(fill='x', pady=10)
        
        self.tabela_historico = ttk.Treeview(historico_frame, columns=("data_emprestimo", "matricula", "data_devolucao"), show="headings")
        self.tabela_historico.heading("data_emprestimo", text="Empréstimo")
        self.tabela_historico.heading("matricula", text="Matrícula do Aluno")
        self.tabela_historico.heading("data_devolucao", text="Devolução")
        self.tabela_historico.pack(fill='both')

        self.atualizar_inventario()

    def interface_usuarios_adm(self):
        frame = ttk.Frame(self.aba_usuarios, padding=20)
        frame.pack(expand=True, fill='both')
        
        cadastro_frame = ttk.LabelFrame(frame, text="Gerenciamento de Usuários", padding=10)
        cadastro_frame.pack(fill='x', pady=10)
        
        cadastro_frame.columnconfigure(0, weight=1)
        cadastro_frame.columnconfigure(1, weight=1)

        ttk.Button(cadastro_frame, text="Cadastrar Novo Usuário", command=self.adicionar_usuario_interface).grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(cadastro_frame, text="Editar Usuário", command=self.editar_usuario_interface).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=20)

        usuarios_frame = ttk.LabelFrame(frame, text="Lista de Usuários", padding=10)
        usuarios_frame.pack(expand=True, fill='both')
        
        self.usuarios_tabela = ttk.Treeview(usuarios_frame, columns=("matricula", "nome", "tipo"), show="headings")
        self.usuarios_tabela.heading("matricula", text="Matrícula")
        self.usuarios_tabela.heading("nome", text="Nome")
        self.usuarios_tabela.heading("tipo", text="Tipo")
        self.usuarios_tabela.pack(expand=True, fill='both')

        self.atualizar_usuarios()

    def interface_logs_adm(self):
        frame = ttk.Frame(self.aba_logs, padding=20)
        frame.pack(expand=True, fill='both')
        ttk.Label(frame, text="Logs de Atividade", font=('Helvetica', 14, 'bold')).pack(pady=10)
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

    def atualizar_usuarios(self):
        for row in self.usuarios_tabela.get_children():
            self.usuarios_tabela.delete(row)
        c.execute("SELECT matricula, nome, tipo FROM usuarios")
        todos_usuarios = c.fetchall()
        for usuario in todos_usuarios:
            self.usuarios_tabela.insert('', 'end', values=usuario)

    def exibir_historico_notebook(self, event):
        item_selecionado = self.inventario_tabela.focus()
        if not item_selecionado:
            return
        
        patrimonio = self.inventario_tabela.item(item_selecionado, 'values')[0]
        
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
        
        ttk.Label(frame, text="Matrícula:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        matricula_entry = ttk.Entry(frame)
        matricula_entry.pack(pady=(0, 10), fill='x')
        ttk.Label(frame, text="Nome:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        nome_entry = ttk.Entry(frame)
        nome_entry.pack(pady=(0, 10), fill='x')
        ttk.Label(frame, text="Tipo:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        tipo_var = tk.StringVar(value="aluno")
        tipo_combo = ttk.Combobox(frame, textvariable=tipo_var, values=["aluno", "professor", "adm"])
        tipo_combo.pack(pady=(0, 10), fill='x')
        ttk.Label(frame, text="Senha:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        senha_entry = ttk.Entry(frame, show="*")
        senha_entry.pack(pady=(0, 10), fill='x')

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
                self.atualizar_usuarios()
            else:
                messagebox.showerror("Erro", message)

        ttk.Button(frame, text="Salvar", command=salvar).pack(pady=10, fill='x')

    def editar_usuario_interface(self):
        item_selecionado = self.usuarios_tabela.focus()
        if not item_selecionado:
            messagebox.showerror("Erro", "Selecione um usuário na tabela para editar.")
            return
        
        matricula, nome, tipo = self.usuarios_tabela.item(item_selecionado, 'values')

        if matricula == 'admin':
            messagebox.showwarning("Aviso", "Não é possível editar o usuário administrador padrão.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Editar Usuário: {matricula}")
        frame = ttk.Frame(win, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text=f"Matrícula: {matricula}", font=('Helvetica', 10, 'bold')).pack(pady=(0, 10), anchor='w')
        
        ttk.Label(frame, text="Nome:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        nome_entry = ttk.Entry(frame)
        nome_entry.insert(0, nome)
        nome_entry.pack(pady=(0, 10), fill='x')

        ttk.Label(frame, text="Tipo:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        tipo_var = tk.StringVar(value=tipo)
        tipo_combo = ttk.Combobox(frame, textvariable=tipo_var, values=["aluno", "professor", "adm"])
        tipo_combo.pack(pady=(0, 10), fill='x')

        def salvar_edicao():
            novo_nome = nome_entry.get()
            novo_tipo = tipo_var.get()
            
            if not novo_nome:
                messagebox.showerror("Erro", "O nome não pode ser vazio.")
                return

            success, message = editar_usuario_db(matricula, novo_nome, novo_tipo)
            if success:
                messagebox.showinfo("Sucesso", message)
                registrar_log(self.usuario_logado[0], f"Usuário {matricula} editado.")
                win.destroy()
                self.atualizar_usuarios()
            else:
                messagebox.showerror("Erro", message)
        
        ttk.Button(frame, text="Salvar Alterações", command=salvar_edicao).pack(pady=10, fill='x')


    def adicionar_notebook_interface(self):
        win = tk.Toplevel(self.root)
        win.title("Cadastrar Notebook")
        frame = ttk.Frame(win, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="Patrimônio:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        patrimonio_entry = ttk.Entry(frame)
        patrimonio_entry.pack(pady=(0, 10), fill='x')
        ttk.Label(frame, text="Marca:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        marca_entry = ttk.Entry(frame)
        marca_entry.pack(pady=(0, 10), fill='x')
        ttk.Label(frame, text="Modelo:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        modelo_entry = ttk.Entry(frame)
        modelo_entry.pack(pady=(0, 10), fill='x')

        def salvar():
            patrimonio = patrimonio_entry.get()
            marca = marca_entry.get()
            modelo = modelo_entry.get()
            if not patrimonio or not marca or not modelo:
                messagebox.showerror("Erro", "Todos os campos de notebook devem ser preenchidos.")
                return
            success, message = adicionar_notebook(patrimonio, marca, modelo)
            if success:
                messagebox.showinfo("Sucesso", message)
                registrar_log(self.usuario_logado[0], f"Notebook {patrimonio} cadastrado.")
                win.destroy()
                self.atualizar_inventario()
            else:
                messagebox.showerror("Erro", message)

        ttk.Button(frame, text="Salvar", command=salvar).pack(pady=10, fill='x')

    def editar_notebook_interface(self):
        item_selecionado = self.inventario_tabela.focus()
        if not item_selecionado:
            messagebox.showerror("Erro", "Selecione um notebook na tabela para editar.")
            return
        
        patrimonio, marca, modelo, status = self.inventario_tabela.item(item_selecionado, 'values')

        win = tk.Toplevel(self.root)
        win.title(f"Editar Notebook: {patrimonio}")
        frame = ttk.Frame(win, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text=f"Patrimônio: {patrimonio}", font=('Helvetica', 10, 'bold')).pack(pady=(0, 10), anchor='w')
        
        ttk.Label(frame, text="Marca:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        marca_entry = ttk.Entry(frame)
        marca_entry.insert(0, marca)
        marca_entry.pack(pady=(0, 10), fill='x')

        ttk.Label(frame, text="Modelo:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        modelo_entry = ttk.Entry(frame)
        modelo_entry.insert(0, modelo)
        modelo_entry.pack(pady=(0, 10), fill='x')

        ttk.Label(frame, text="Status:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        status_var = tk.StringVar(value=status)
        status_combo = ttk.Combobox(frame, textvariable=status_var, values=["Disponível", "Emprestado", "Em Manutenção", "Estragado"])
        status_combo.pack(pady=(0, 10), fill='x')

        def salvar_edicao():
            nova_marca = marca_entry.get()
            novo_modelo = modelo_entry.get()
            novo_status = status_var.get()
            
            if not nova_marca or not novo_modelo:
                messagebox.showerror("Erro", "Marca e Modelo não podem ser vazios.")
                return

            if status == 'Emprestado' and novo_status in ('Em Manutenção', 'Estragado'):
                messagebox.showwarning("Aviso", "Não é possível alterar o status de um notebook emprestado para manutenção ou estragado.")
                return

            success, message = editar_notebook_db(patrimonio, nova_marca, novo_modelo, novo_status)
            if success:
                messagebox.showinfo("Sucesso", message)
                registrar_log(self.usuario_logado[0], f"Notebook {patrimonio} editado.")
                win.destroy()
                self.atualizar_inventario()
            else:
                messagebox.showerror("Erro", message)
        
        ttk.Button(frame, text="Salvar Alterações", command=salvar_edicao).pack(pady=10, fill='x')

    def alterar_status_notebook_interface(self):
        item_selecionado = self.inventario_tabela.focus()
        if not item_selecionado:
            messagebox.showerror("Erro", "Selecione um notebook na tabela para alterar o status.")
            return

        patrimonio, _, _, status = self.inventario_tabela.item(item_selecionado, 'values')
        
        win = tk.Toplevel(self.root)
        win.title(f"Alterar Status de {patrimonio}")
        frame = ttk.Frame(win, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text=f"Status atual: {status}", font=('Helvetica', 10, 'bold')).pack(pady=(0, 5), anchor='w')
        
        ttk.Label(frame, text="Novo Status:", font=('Helvetica', 10)).pack(pady=(0, 5), anchor='w')
        status_var = tk.StringVar()
        status_combo = ttk.Combobox(frame, textvariable=status_var, values=["Disponível", "Em Manutenção", "Estragado"])
        status_combo.pack(pady=(0, 10), fill='x')
        status_combo.set(status)

        def salvar_status():
            novo_status = status_var.get()
            if not novo_status:
                messagebox.showerror("Erro", "Selecione um status.")
                return
            
            if status == 'Emprestado' and novo_status in ('Em Manutenção', 'Estragado'):
                messagebox.showwarning("Aviso", "Não é possível alterar o status de um notebook emprestado para manutenção ou estragado.")
                return

            atualizar_status_notebook(patrimonio, novo_status)
            registrar_log(self.usuario_logado[0], f"Status do notebook {patrimonio} alterado para {novo_status}.")
            messagebox.showinfo("Sucesso", f"Status do notebook {patrimonio} alterado para {novo_status}.")
            win.destroy()
            self.atualizar_inventario()

        ttk.Button(frame, text="Salvar", command=salvar_status).pack(pady=10, fill='x')


# Inicia a aplicação
if __name__ == "__main__":
    root = ThemedTk(theme="azure")
    app = App(root)
    root.mainloop()