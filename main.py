import os
import sys
import random 
import pygame


def caminho_recurso(nome):
    """Devolve o caminho completo de um arquivo do jogo (imagem ou som).

    Funciona tanto rodando o .py (usa a pasta onde está o main.py)
    quanto dentro do .exe (usa a pasta temporária do PyInstaller).
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, nome)

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

# Tela
LARGURA = 800
ALTURA = 600
FPS = 60

# Cores (RGB)
COR_FUNDO = (135, 206, 235)
COR_BRANCO = (255, 255, 255)
COR_SOMBRA = (30, 30, 30)
COR_GAME_OVER = (200, 0, 0)

# Tamanhos (altura visível de cada imagem, em pixels)
ALTURA_CHAO = 60
ALTURA_URSO = 90
ALTURA_TRONCO = 80

# Quanto os pés do urso e a base do tronco "afundam" na selva.
PE_NO_CHAO = 10

# Movimento
VELOCIDADE_INICIAL = 6      # velocidade no começo da rodada
AUMENTO_VELOCIDADE = 1.2    # multiplicador: 1.2 = +20%
PONTOS_POR_NIVEL = 10       # a cada quantos pontos a velocidade aumenta
VELOCIDADE_MAXIMA = 18      # limite, para o jogo não ficar impossível
GRAVIDADE = 0.8
FORCA_PULO = -14      # negativo porque o eixo Y cresce para baixo
URSO_X = 100          # posição horizontal fixa do urso

# Caixas de colisão: (margem lateral, margem do topo, margem da base)
# Cada valor é uma fração do tamanho da imagem. A caixa fica um pouco
# menor que o desenho para a colisão parecer justa para o jogador.
HITBOX_URSO = (0.25, 0.12, 0.03)
HITBOX_TRONCO = (0.20, 0.10, 0.0)

# Estados do jogo
ESTADO_INICIO = "INICIO"
ESTADO_JOGANDO = "JOGANDO"
ESTADO_GAME_OVER = "GAME_OVER"

#Som do pulo
VOLUME_PULO = 0.5   # de 0.0 (mudo) a 1.0 (máximo)

#Som da música de fundo
VOLUME_MUSICA = 0.3   # de 0.0 a 1.0; música de fundo costuma ficar mais baixa que os efeitos

#Volume som o game over
VOLUME_GAME_OVER = 0.5

#Altura e tamanho do sol
ALTURA_SOL = 100      # altura do sol em pixels
MARGEM_SOL = 30       # distância do sol até o canto da tela

# Nuvens
ARQUIVOS_NUVENS = ["nuvem01.png", "nuvem02.png", "nuvem03.png"]
QUANTIDADE_NUVENS = 4     # quantas nuvens aparecem ao mesmo tempo
ALTURA_NUVEM = 60         # altura das imagens em pixels
NUVEM_Y_MIN = 50          # faixa de altura onde as nuvens aparecem
NUVEM_Y_MAX = 200
NUVEM_VEL_MIN = 0.6       # velocidade mínima (bem mais lenta que o chão)
NUVEM_VEL_MAX = 1.2       # velocidade máxima

# Mude para True para ver as caixas de colisão
MOSTRAR_HITBOX = False

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def carregar_imagem(arquivo, altura_final):
    """Carrega um PNG, corta as bordas transparentes e ajusta a altura.
    Os PNGs costumam ter margem invisível ao redor do desenho. Sem cortar,
    o objeto parece flutuar ou menor do que deveria. A largura é calculada
    pela proporção original, então a imagem não fica esticada.
    """
    imagem = pygame.image.load(caminho_recurso(arquivo)).convert_alpha()
    area_visivel = imagem.get_bounding_rect(min_alpha=20)  # ignora pixels quase invisíveis
    imagem = imagem.subsurface(area_visivel).copy()

    proporcao = altura_final / imagem.get_height()
    largura_final = int(imagem.get_width() * proporcao)
    return pygame.transform.scale(imagem, (largura_final, altura_final))


def criar_hitbox(x, y, largura, altura, margens):
    """Cria o retângulo de colisão a partir da posição e do tamanho do desenho."""
    margem_lateral, margem_topo, margem_base = margens
    return pygame.Rect(
        int(x + largura * margem_lateral),
        int(y + altura * margem_topo),
        int(largura * (1 - 2 * margem_lateral)),
        int(altura * (1 - margem_topo - margem_base)),
    )


def desenhar_texto(tela, fonte, texto, cor, centro, com_sombra=False):
    """Desenha um texto centralizado em 'centro', com sombra opcional."""
    if com_sombra:
        sombra = fonte.render(texto, True, COR_SOMBRA)
        tela.blit(sombra, sombra.get_rect(center=(centro[0] + 2, centro[1] + 2)))
    superficie = fonte.render(texto, True, cor)
    tela.blit(superficie, superficie.get_rect(center=centro))


def desenhar_texto_canto(tela, fonte, texto, cor, posicao):
    """Desenha um texto com o canto superior esquerdo em 'posicao', com sombra."""
    sombra = fonte.render(texto, True, COR_SOMBRA)
    tela.blit(sombra, (posicao[0] + 2, posicao[1] + 2))
    superficie = fonte.render(texto, True, cor)
    tela.blit(superficie, posicao)


# ==========================================================
# CLASSES DO JOGO
# Cada classe guarda os dados de um elemento do jogo e sabe
# se atualizar e se desenhar sozinha.
# ==========================================================

class Chao:
    """Chão infinito: duas faixas iguais andando para a esquerda, uma atrás da outra."""

    def __init__(self):
        bloco = carregar_imagem("chao.png", ALTURA_CHAO)
        largura_bloco = bloco.get_width()

        # A faixa tem largura múltipla do bloco, então nenhum bloco é cortado
        # no meio e a emenda entre as faixas fica perfeita.
        blocos_por_faixa = LARGURA // largura_bloco + 1
        self.largura = blocos_por_faixa * largura_bloco

        self.faixa = pygame.Surface((self.largura, ALTURA_CHAO), pygame.SRCALPHA)
        for i in range(blocos_por_faixa):
            self.faixa.blit(bloco, (i * largura_bloco, 0))

        self.y = ALTURA - ALTURA_CHAO              # o chão encosta no fim da tela
        self.linha_de_apoio = self.y + PE_NO_CHAO  # onde urso e tronco se apoiam

        self.x1 = 0
        self.x2 = self.largura

    def atualizar(self, velocidade):
        self.x1 -= velocidade
        self.x2 -= velocidade

        # Quando uma faixa sai da tela, ela volta para logo depois da outra.
        if self.x1 <= -self.largura:
            self.x1 = self.x2 + self.largura
        if self.x2 <= -self.largura:
            self.x2 = self.x1 + self.largura

    def desenhar(self, tela):
        tela.blit(self.faixa, (self.x1, self.y))
        tela.blit(self.faixa, (self.x2, self.y))


class Urso:
    """O jogador: fica parado na horizontal e só se move para cima e para baixo."""

    def __init__(self, linha_de_apoio):
        self.imagem = carregar_imagem("urso.png", ALTURA_URSO)
        self.largura = self.imagem.get_width()
        self.altura = ALTURA_URSO
        self.x = URSO_X
        self.y_chao = linha_de_apoio - self.altura  # valor de y quando está no chão
        self.reiniciar()
        self.som_pulo = pygame.mixer.Sound(caminho_recurso("pulo.wav"))
        self.som_pulo.set_volume(VOLUME_PULO)

    def reiniciar(self):
        """Coloca o urso de volta na posição inicial."""
        self.y = self.y_chao
        self.velocidade_y = 0
        self.no_chao = True

    def pular(self):
        # Só pula se estiver no chão (sem pulo duplo no ar).
        if self.no_chao:
            self.velocidade_y = FORCA_PULO
            self.no_chao = False
            self.som_pulo.play()

    def atualizar(self):
        # A gravidade aumenta a velocidade de queda a cada quadro.
        self.velocidade_y += GRAVIDADE
        self.y += self.velocidade_y

        # Ao tocar o chão, para de cair.
        if self.y >= self.y_chao:
            self.y = self.y_chao
            self.velocidade_y = 0
            self.no_chao = True

    def hitbox(self):
        return criar_hitbox(self.x, self.y, self.largura, self.altura, HITBOX_URSO)

    def desenhar(self, tela):
        tela.blit(self.imagem, (self.x, self.y))


class Tronco:
    """Obstáculo: anda para a esquerda e reaparece do lado direito ao sair da tela."""

    def __init__(self, linha_de_apoio):
        self.imagem = carregar_imagem("tronco.png", ALTURA_TRONCO)
        self.largura = self.imagem.get_width()
        self.altura = ALTURA_TRONCO
        self.y = linha_de_apoio - self.altura
        self.reiniciar()

    def reiniciar(self):
        self.x = LARGURA
        self.ja_pontuou = False

    def atualizar(self, velocidade):
        self.x -= velocidade
        if self.x < -self.largura:
            self.x = LARGURA
            self.ja_pontuou = False

    def hitbox(self):
        return criar_hitbox(self.x, self.y, self.largura, self.altura, HITBOX_TRONCO)

    def desenhar(self, tela):
        tela.blit(self.imagem, (self.x, self.y))

class Nuvem:
    """Nuvem de fundo: anda devagar para a esquerda e reaparece do lado direito."""

    def __init__(self, imagens, x_inicial):
        self.imagens = imagens
        self.sortear(x_inicial)

    def sortear(self, x):
        """Sorteia imagem, altura e velocidade, e coloca a nuvem na posição x."""
        self.imagem = random.choice(self.imagens)
        self.largura = self.imagem.get_width()
        self.x = x
        self.y = random.randint(NUVEM_Y_MIN, NUVEM_Y_MAX)
        self.velocidade = random.uniform(NUVEM_VEL_MIN, NUVEM_VEL_MAX)

    def atualizar(self):
        self.x -= self.velocidade
        # Saiu inteira pela esquerda: reaparece à direita, com sorteio novo.
        if self.x < -self.largura:
            self.sortear(LARGURA + random.randint(0, 150))

    def desenhar(self, tela):
        tela.blit(self.imagem, (int(self.x), self.y))

# ==========================================================
# PROGRAMA PRINCIPAL
# ==========================================================

def main():
    pygame.init()
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Urso Run")
    pygame.mixer.music.load(caminho_recurso("musica.ogg"))
    pygame.mixer.music.set_volume(VOLUME_MUSICA)
    relogio = pygame.time.Clock()

    fonte_inicio = pygame.font.SysFont("arial", 32, bold=True)
    fonte_game_over = pygame.font.SysFont(None, 48)
    fonte_score = pygame.font.SysFont("arial", 32, bold=True)

    # As imagens só podem ser carregadas depois do set_mode,
    # por isso os objetos são criados aqui e não no topo do arquivo.
    chao = Chao()
    urso = Urso(chao.linha_de_apoio)
    tronco = Tronco(chao.linha_de_apoio)

    #sol no canto superior direito
    imagem_sol = carregar_imagem("sol.png", ALTURA_SOL)
    posicao_sol = (LARGURA - imagem_sol.get_width() - MARGEM_SOL, MARGEM_SOL)

    #nuvens
    imagens_nuvens = [carregar_imagem(arquivo, ALTURA_NUVEM) for arquivo in ARQUIVOS_NUVENS]
    nuvens = [
        Nuvem(imagens_nuvens, i * LARGURA // QUANTIDADE_NUVENS)
        for i in range(QUANTIDADE_NUVENS)
    ]

    #som de game over
    som_game_over = pygame.mixer.Sound(caminho_recurso("musicaover.wav"))
    som_game_over.set_volume(VOLUME_GAME_OVER)

    estado = ESTADO_INICIO
    pontos = 0
    rodando = True

    while rodando:
        # --- 1. EVENTOS (teclado e janela) ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_SPACE:
                if estado == ESTADO_INICIO:
                    estado = ESTADO_JOGANDO
                    pygame.mixer.music.play(-1)
                elif estado == ESTADO_JOGANDO:
                    urso.pular()
                elif estado == ESTADO_GAME_OVER:
                    urso.reiniciar()
                    tronco.reiniciar()
                    pontos = 0
                    estado = ESTADO_JOGANDO
                    pygame.mixer.music.play(-1)

        # --- 2. ATUALIZAR (só quando o jogo está rolando) ---
        for nuvem in nuvens:          #as nuvens se movem em qualquer estado
            nuvem.atualizar()

        if estado == ESTADO_JOGANDO:
            velocidade = min(
                VELOCIDADE_INICIAL * AUMENTO_VELOCIDADE ** (pontos // PONTOS_POR_NIVEL),
                VELOCIDADE_MAXIMA,
            )
            chao.atualizar(velocidade)
            tronco.atualizar(velocidade)
            urso.atualizar()

            if urso.hitbox().colliderect(tronco.hitbox()):
                estado = ESTADO_GAME_OVER
                pygame.mixer.music.stop()
                som_game_over.play()

            if not tronco.ja_pontuou and tronco.x + tronco.largura < urso.x:
                pontos += 1
                tronco.ja_pontuou = True

        # --- 3. DESENHAR (de trás para frente) ---
        tela.fill(COR_FUNDO)
        tela.blit(imagem_sol, posicao_sol)    #o sol vem logo depois do fundo
        for nuvem in nuvens:          #as nuvens passam na frente do sol
            nuvem.desenhar(tela)
        chao.desenhar(tela)
        tronco.desenhar(tela)
        urso.desenhar(tela)

        #placar no canto superior esquerdo
        if estado != ESTADO_INICIO:
            desenhar_texto_canto(tela, fonte_score, f"{pontos:04d}", COR_BRANCO, (20, 20))

        if MOSTRAR_HITBOX:
            pygame.draw.rect(tela, (255, 0, 0), urso.hitbox(), 2)
            pygame.draw.rect(tela, (255, 0, 0), tronco.hitbox(), 2)
            pygame.draw.line(tela, (0, 0, 255),
                             (0, chao.linha_de_apoio), (LARGURA, chao.linha_de_apoio))

        centro_tela = (LARGURA // 2, ALTURA // 2)
        if estado == ESTADO_INICIO:
            desenhar_texto(tela, fonte_inicio, "START GAME", COR_BRANCO,
                           centro_tela, com_sombra=True)
        elif estado == ESTADO_GAME_OVER:
            desenhar_texto(tela, fonte_game_over, "GAME OVER", COR_GAME_OVER,
                           centro_tela)

        pygame.display.flip()
        relogio.tick(FPS)

    pygame.quit()
    sys.exit()


# Só roda o jogo se este arquivo for executado diretamente
# (e não se for importado por outro arquivo).
if __name__ == "__main__":
    main()