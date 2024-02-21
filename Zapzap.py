import socket
import threading
import os
import pickle
import time
from Config import *
from Classes import *
from Criptography import encrypt, decrypt

print(whatsApp2)

# Testa se você está online
if socket.gethostbyname(socket.gethostbyname(socket.gethostname())) == "127.0.0.1":
    print("ERRO! Você não está conectado a nenhuma rede.")
    exit()

# Dados
conversa = set()
membros = []
pkgCache = [] # Cache temporário de pacotes

clock = LamportClock()
Contatos().initialize()

# Informações do usuário
nome_usuario = input("Digite o seu usuário: ")
usuario_obj: Membro = Contatos().get_contato(nome_usuario)
while usuario_obj == None or usuario_obj.address[0] != socket.gethostbyname(socket.gethostname()):
    nome_usuario = input("Usuário inválido! Digite o seu usuário: ")
    usuario_obj = Contatos().get_contato(nome_usuario)

usuario_obj.status = ON
membros.append(usuario_obj)

HOST = usuario_obj.address[0]
PORT = usuario_obj.address[1]

# Informações do grupo
nomes_membros = input("Insira os membros: ")
for nome_membro in nomes_membros.split():
    membro_obj: Membro = Contatos().get_contato(nome_membro)
    membros.append(membro_obj)

password = input("Insira a senha de criptografia do grupo: ")

# Envia pacotes
def send_message(sock, clock, message, membros, type):
    try:
        logicstamp = 0
        
        if type == SYN:
            logicstamp = clock.increment()
        if type == MSG:
            logicstamp = clock.increment()
            mensagem = Mensagem(usuario_obj, message, logicstamp, membros)
            conversa.update([mensagem])

        data = pickle.dumps((message, logicstamp, type))
        for membro in membros:
            if membro.address != (HOST, PORT):
                sock.sendto(data, membro.address)

    except socket.error as e:
        print(f"Erro de conexão! {e.strerror}\nTente novamente mais tarde...")
        time.sleep(5)
        exit()

# Envia a sua conversa
def sendChat(sock, adress):
    try:
        for mensagemOBJ in conversa:
            logicstamp = 0
            partMessage = pickle.dumps(mensagemOBJ)
            data = pickle.dumps((partMessage, logicstamp, CSP))
            sock.sendto(data, adress)
            
    except socket.error as e:
        print(f"Erro de conexão! {e.strerror}\nTente novamente mais tarde...")
        time.sleep(5)
        exit()

# Recebe pacotes
def listner(sock, clock):
    while True:
        try:
            pacote = sock.recvfrom(1024)
            pkgCache.append(pacote)
        except:
            pass

# Trata os pacotes recebidos
def pkgSort(sock, clock):
    while True:
        if len(pkgCache) > 0:
            data, address = pkgCache.pop() # Tupla contendo Data e ClientAddress (nessa ordem)
            message, received_time, type = pickle.loads(data) # Interpreta o Data

            if type == MSG or type == SYN:
                clock.update(received_time)

            if type == MSG:
                msg_dono = Contatos().get_contato_by_address(address)
                mensagem = Mensagem(msg_dono, message, received_time, membros)
                conversa.update([mensagem])
                printSort()

            elif type == SYN and (message == 'first' or message == 'syncRequest'):
                send_message(sock, clock, None, membros, SYN) # Mensagem para sincronizar o relógio
                sendChat(sock, address)

            elif type == CSP:
                messageOBJ = pickle.loads(message)
                conversa.update([messageOBJ])
            
            elif type == PING:
                send_message(sock, clock, None, membros, PING_ACK)

            elif type == PING_ACK:
                for membro in membros:
                    if membro.address == address:
                        membro.status = ON

# Envia pings
def online_requester(sock, clock):
    while True:
        try:
            data = pickle.dumps(('', 0, PING))
            for membro in membros:
                if membro.address != (HOST, PORT):
                    if membro.status == ON:
                        membro.status = UKN
                    elif membro.status == UKN:
                        membro.status = OFF

                    sock.sendto(data, membro.address)

        except socket.error as e:
            print(f"Erro de conexão! {e.strerror}\nTente novamente mais tarde...")
            time.sleep(5)
            exit()

        finally:
            time.sleep(ONLINE_SYNC_TIME)

# Ordena as mensagens
def consensusSort(sortableChat):
    if bool(sortableChat):
        sortableChat.sort(key=lambda x: (x.logicstamp, x.user.address))

# Mostra as mensagens em ordem
def printSort():
    sortableChat = list(conversa)
    consensusSort(sortableChat)

    # Otimiza a lista para mostrar apenas as 20 últimas mensagens
    if OPTIMIZE_PRINT and len(sortableChat) > OPTIMIZE_SIZE:
        sortableChat = sortableChat[-OPTIMIZE_SIZE:]
    
    # Exibe na tela
    os.system(LIMPAR)
    for msg in sortableChat:
        msg: Mensagem
        colorIndex = f"\033[38;5;{(sum(int(digito) for digito in msg.user.address[0] if digito.isdigit()) + msg.user.address[1] ) % (255 + 1)}m"

        if (msg.user.address[0] == HOST and msg.user.address[1] == PORT):
            print(f'{colorIndex}Você\033[0m: {decrypt(msg.texto, password)}')
        else:
            print(f'{colorIndex}{msg.user.name} - {msg.user.address} ({msg.user.status}) \033[0m: {decrypt(msg.texto, password)}')
    print("on screen chatsize: ", len(sortableChat))

    del sortableChat

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))

    # Threads secundárias
    package_listner_thread = threading.Thread(target=listner, args=(sock, clock), daemon=True)
    package_listner_thread.start()

    package_sort_thread = threading.Thread(target=pkgSort, args=(sock, clock), daemon=True)
    package_sort_thread.start()

    online_requester_thread = threading.Thread(target= online_requester, args=(sock, clock), daemon=True)
    online_requester_thread.start()

    # while True: # para teste: Mostra em tempo real o status do usuário
    #     string = ""
    #     for membro in membros:
    #         string += "\n" + f"{membro.name} - {membro.address}: {membro.status}" 
    #     os.system(LIMPAR)
    #     print(string)
    #     time.sleep(0.16)

    # First message
    send_message(sock, clock, 'first', membros, SYN)
    while True:
        message = input(">:")
        while message == '':
            message = input(">:")

        if message[0] == "/":
            if message == "/help":
                help_str = '''
Lista de comandos:
/membros -> Vê os membros do grupo e seu status online ou offline
/chave -> Vê a chave de criptografia do grupo'''
                os.system(LIMPAR)
                print(help_str)

            elif message == "/membros":
                os.system(LIMPAR)
                for membro in membros:
                    print(f"{membro.name} - {membro.address[0]} ({membro.status}) ")

            elif message == "/chave":
                os.system(LIMPAR)
                print(f"Chave de criptografia: {password}")

            else:
                os.system(LIMPAR)
                print(f"Comando desconhecido! tente /help")

        else:
            send_message(sock, clock, encrypt(message, password), membros, MSG)
            printSort()

if __name__ == "__main__":
    main()