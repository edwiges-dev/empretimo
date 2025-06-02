import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

# ====== BANCO DE DADOS ======

def criar_banco():
    conexao = sqlite3.connect("emprestimos.db")
    cursor = conexao.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            matricula TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            tipo TEXT CHECK(tipo IN ('aluno', 'professor')) NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notebooks (
            patrimonio TEXT PRIMARY KEY,
            status TEXT CHECK(status IN ('disponivel', 'emprestado')) NOT NULL,
            emprestado_para TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emprestimos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio TEXT NOT NULL,
            matricula TEXT NOT NULL,
            data_emprestimo TEXT NOT NULL,
            data_devolucao TEXT NOT NULL,
            devolvido INTEGER DEFAULT 0,
            FOREIGN KEY(patrimonio) REFERENCES notebooks(patrimonio),
            FOREIGN KEY(matricula) REFERENCES usuarios(matricula)
        )
    ''')

    conexao.commit()
    conexao.close()

criar_banco()

# ====== FUNÇÕES DO SISTEMA ======

def cadastrar_usuario():
    def salvar():
        matricula = entrada_matricula.get()
        nome = entrada_nome.get()
        tipo = combo_tipo.get()

        if not matricula or not nome or not tipo:
            messagebox.showerror("Erro", "Preencha todos os campos.")
            return

        conexao = sqlite3.connect("emprestimos.db")
        cursor = conexao.cursor()
        try:
            cursor.execute("INSERT INTO usuarios VALUES (?, ?, ?)", (matricula, nome, tipo))
            conexao.commit()
            messagebox.showinfo("Sucesso", "Usuário cadastrado.")
            janela.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Matrícula já cadastrada.")
        finally:
            conexao.close()

    janela = tk.Toplevel()
    janela.title("Cadastrar Usuário")

    tk.Label(janela, text="Matrícula:").pack()
    entrada_matricula = tk.Entry(janela)
    entrada_matricula.pack()

    tk.Label(janela, text="Nome:").pack()
    entrada_nome = tk.Entry(janela)
    entrada_nome.pack()

    tk.Label(janela, text="Tipo:").pack()
    combo_tipo = ttk.Combobox(janela, values=["aluno", "professor"])
    combo_tipo.pack()

    tk.Button(janela, text="Salvar", command=salvar).pack(pady=5)

def cadastrar_notebook():
    def salvar():
        patrimonio = entrada_patrimonio.get()
        if not patrimonio:
            messagebox.showerror("Erro", "Informe o número de patrimônio.")
            return

        conexao = sqlite3.connect("emprestimos.db")
        cursor = conexao.cursor()
        try:
            cursor.execute("INSERT INTO notebooks VALUES (?, 'disponivel', NULL)", (patrimonio,))
            conexao.commit()
            messagebox.showinfo("Sucesso", "Notebook cadastrado.")
            janela.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Patrimônio já cadastrado.")
        finally:
            conexao.close()

    janela = tk.Toplevel()
    janela.title("Cadastrar Notebook")

    tk.Label(janela, text="Número de Patrimônio:").pack()
    entrada_patrimonio = tk.Entry(janela)
    entrada_patrimonio.pack()

    tk.Button(janela, text="Salvar", command=salvar).pack(pady=5)

def emprestar_notebook():
    def salvar():
        patrimonio = combo_patrimonio.get()
        matricula = entrada_matricula.get()
        dias = entrada_prazo.get()

        if not patrimonio or not matricula or not dias:
            messagebox.showerror("Erro", "Preencha todos os campos.")
            return

        try:
            dias = int(dias)
        except ValueError:
            messagebox.showerror("Erro", "Prazo deve ser um número de dias.")
            return

        data_emprestimo = datetime.now()
        data_devolucao = data_emprestimo + timedelta(days=dias)

        conexao = sqlite3.connect("emprestimos.db")
        cursor = conexao.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE matricula = ?", (matricula,))
        if not cursor.fetchone():
            messagebox.showerror("Erro", "Matrícula não encontrada.")
            conexao.close()
            return

        cursor.execute("UPDATE notebooks SET status = 'emprestado', emprestado_para = ? WHERE patrimonio = ?", (matricula, patrimonio))
        cursor.execute("INSERT INTO emprestimos (patrimonio, matricula, data_emprestimo, data_devolucao) VALUES (?, ?, ?, ?)",
                       (patrimonio, matricula, data_emprestimo.strftime("%Y-%m-%d"), data_devolucao.strftime("%Y-%m-%d")))
        conexao.commit()
        conexao.close()
        messagebox.showinfo("Sucesso", "Notebook emprestado.")
        janela.destroy()

    janela = tk.Toplevel()
    janela.title("Emprestar Notebook")

    tk.Label(janela, text="Matrícula do Usuário:").pack()
    entrada_matricula = tk.Entry(janela)
    entrada_matricula.pack()

    tk.Label(janela, text="Número de Patrimônio:").pack()
    conexao = sqlite3.connect("emprestimos.db")
    cursor = conexao.cursor()
    cursor.execute("SELECT patrimonio FROM notebooks WHERE status = 'disponivel'")
    disponiveis = [row[0] for row in cursor.fetchall()]
    conexao.close()

    combo_patrimonio = ttk.Combobox(janela, values=disponiveis)
    combo_patrimonio.pack()

    tk.Label(janela, text="Prazo (em dias):").pack()
    entrada_prazo = tk.Entry(janela)
    entrada_prazo.pack()

    tk.Button(janela, text="Emprestar", command=salvar).pack(pady=5)

def devolver_notebook():
    def devolver():
        patrimonio = combo.get()
        if not patrimonio:
            messagebox.showerror("Erro", "Selecione um notebook.")
            return

        conexao = sqlite3.connect("emprestimos.db")
        cursor = conexao.cursor()
        cursor.execute("UPDATE notebooks SET status = 'disponivel', emprestado_para = NULL WHERE patrimonio = ?", (patrimonio,))
        cursor.execute("UPDATE emprestimos SET devolvido = 1 WHERE patrimonio = ? AND devolvido = 0", (patrimonio,))
        conexao.commit()
        conexao.close()
        messagebox.showinfo("Sucesso", "Notebook devolvido.")
        janela.destroy()

    janela = tk.Toplevel()
    janela.title("Devolver Notebook")

    conexao = sqlite3.connect("emprestimos.db")
    cursor = conexao.cursor()
    cursor.execute("SELECT patrimonio FROM notebooks WHERE status = 'emprestado'")
    emprestados = [row[0] for row in cursor.fetchall()]
    conexao.close()

    tk.Label(janela, text="Notebook a Devolver:").pack()
    combo = ttk.Combobox(janela, values=emprestados)
    combo.pack()

    tk.Button(janela, text="Devolver", command=devolver).pack(pady=5)

def mostrar_aviso_devolucoes():
    hoje = datetime.now().strftime("%Y-%m-%d")
    conexao = sqlite3.connect("emprestimos.db")
    cursor = conexao.cursor()
    cursor.execute("SELECT patrimonio, matricula, data_devolucao FROM emprestimos WHERE devolvido = 0 AND data_devolucao < ?", (hoje,))
    atrasados = cursor.fetchall()
    conexao.close()

    if not atrasados:
        messagebox.showinfo("Devoluções", "Nenhum notebook em atraso.")
    else:
        msg = "Notebooks em atraso:\n"
        for p, m, d in atrasados:
            msg += f"Patrimônio {p} - Matrícula {m} (Devolver até: {d})\n"
        messagebox.showwarning("Atenção", msg)

# ====== INTERFACE PRINCIPAL ======

janela = tk.Tk()
janela.title("Sistema de Empréstimo de Notebooks")

ttk.Button(janela, text="Cadastrar Usuário", command=cadastrar_usuario).pack(padx=10, pady=5)
ttk.Button(janela, text="Cadastrar Notebook", command=cadastrar_notebook).pack(padx=10, pady=5)
ttk.Button(janela, text="Emprestar Notebook", command=emprestar_notebook).pack(padx=10, pady=5)
ttk.Button(janela, text="Devolver Notebook", command=devolver_notebook).pack(padx=10, pady=5)
ttk.Button(janela, text="Verificar Devoluções Pendentes", command=mostrar_aviso_devolucoes).pack(padx=10, pady=10)

janela.mainloop()
