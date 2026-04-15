"""
Teste de Comunicao MT5 <-> Python

Este script testa a comunicao TCP Socket entre o EA no MT5 e o Python.
Pode ser executado de duas formas:

1. Simulao (sem MT5): Testa o servidor socket com dados simulados
2. Real (com MT5): Testa com EA real rodando no MT5

Uso:
    python test_mt5_connection.py --mode=simulated    # Simulao
    python test_mt5_connection.py --mode=real         # Real (requer MT5)
"""

import sys
import os
import time
import threading
from datetime import datetime
import argparse

# Adicionar projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.mt5_bridge import MT5Bridge, TickData, ConnectionState
from live_trading.logger import get_logger, get_logger_stats
import logging


def setup_basic_logging():
    """Configura logging bsico para o teste"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def test_simulated():
    """Teste com dados simulados (sem MT5)"""
    print("=" * 80)
    print("TESTE SIMULADO - Comunicao MT5 <-> Python")
    print("=" * 80)
    print()
    
    logger = get_logger("TestSimulated")
    logger.info("Iniciando teste simulado...")
    
    # Criar bridge
    bridge = MT5Bridge(host="127.0.0.1", port=5555)
    
    # Registrar callbacks
    def on_tick(tick):
        logger.info(f" Tick recebido: {tick.symbol} bid={tick.bid:.2f} ask={tick.ask:.2f}")
    
    def on_connected():
        logger.info(" MT5 conectado!")
    
    def on_disconnected():
        logger.warning(" MT5 desconectado")
    
    def on_error(error):
        logger.error(f" Erro: {error}")
    
    bridge.register_callbacks(
        on_tick=on_tick,
        on_connected=on_connected,
        on_disconnected=on_disconnected,
        on_error=on_error
    )
    
    # Iniciar bridge
    logger.info("Iniciando TCP socket server...")
    bridge.start()
    
    # Simular conexo MT5 (client socket)
    logger.info("Simulando conexo MT5...")
    
    try:
        import socket
        
        # Criar client socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", 5555))
        client.settimeout(2)
        
        logger.info("Client socket conectado!")
        
        # Enviar handshake
        handshake = "HANDSHAKE|TestClient|v1.00|20260413\n"
        client.send(handshake.encode())
        logger.info(f"Handshake enviado: {handshake.strip()}")
        
        # Esperar ack
        time.sleep(0.5)
        try:
            ack = client.recv(1024).decode()
            logger.info(f"Ack recebido: {ack}")
        except socket.timeout:
            logger.warning("Timeout esperando ack")
        
        # Enviar ticks simulados
        logger.info("Enviando ticks simulados...")
        
        base_price = 105000.0
        for i in range(10):
            bid = base_price + (i % 3) * 10
            ask = bid + 5
            volume = 100 + i * 10
            spread = ask - bid
            
            tick_msg = f"TICK|BTCUSD|{bid:.2f}|{ask:.2f}|{volume}|{spread:.2f}|150.5|65.2|105100.0|105050.0|104900.0|104500.0|50.5|45.2|{datetime.now().isoformat()}\n"
            
            client.send(tick_msg.encode())
            logger.info(f"Tick {i+1}/10 enviado")
            
            time.sleep(0.5)
        
        # Verificar estatsticas
        time.sleep(1)
        stats = bridge.get_stats()
        logger.info(f"Estatsticas: {stats}")
        
        # Testar envio de sinal
        logger.info("Testando envio de sinal BUY...")
        success = bridge.send_signal("BUY", symbol="BTCUSD", lot=0.01, sl=104500, tp=106000)
        logger.info(f"Sinal enviado: {success}")
        
        # Fechar client
        client.close()
        logger.info("Client socket fechado")
        
        # Aguardar reconexo
        time.sleep(2)
        
        # Reconectar
        logger.info("Testando reconexo...")
        client2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client2.connect(("127.0.0.1", 5555))
        client2.settimeout(2)
        
        handshake2 = "HANDSHAKE|TestClient2|v1.00|20260413\n"
        client2.send(handshake2.encode())
        
        time.sleep(0.5)
        try:
            ack2 = client2.recv(1024).decode()
            logger.info(f"Reconexo OK: {ack2}")
        except:
            pass
        
        client2.close()
        
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Parar bridge
        logger.info("Parando bridge...")
        bridge.stop()
    
    # Resumo
    print()
    print("=" * 80)
    print("RESUMO DO TESTE")
    print("=" * 80)
    
    stats = bridge.get_stats()
    print(f"Ticks recebidos: {stats['ticks_received']}")
    print(f"Sinais enviados: {stats['signals_sent']}")
    print(f"Erros: {stats['errors']}")
    print(f"Reconexes: {stats['reconnections']}")
    print(f"Latncia mdia: {stats['avg_latency_ms']:.2f}ms")
    
    if stats['ticks_received'] > 0 and stats['errors'] == 0:
        print("\n TESTE PASSOU COM SUCESSO!")
    else:
        print("\n TESTE COM PROBLEMAS - Verificar logs")
    
    print("=" * 80)


def test_real():
    """Teste real com MT5 (requer EA rodando)"""
    print("=" * 80)
    print("TESTE REAL - Comunicao MT5 <-> Python")
    print("=" * 80)
    print()
    print(" Certifique-se que:")
    print("1. MetaTrader 5 est aberto")
    print("2. ForexQuantumBot_EA_V3.mq5 est compilado e rodando")
    print("3. EA est configurado com Socket Host: 127.0.0.1, Port: 5555")
    print()
    
    resposta = input("Continuar? (s/n): ")
    if resposta.lower() != 's':
        print("Teste cancelado")
        return
    
    logger = get_logger("TestReal")
    logger.info("Iniciando teste real...")
    
    # Criar bridge
    bridge = MT5Bridge(host="127.0.0.1", port=5555)
    
    # Contador de ticks
    tick_count = 0
    start_time = None
    
    # Registrar callbacks
    def on_tick(tick):
        nonlocal tick_count, start_time
        tick_count += 1
        
        if start_time is None:
            start_time = datetime.now()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        ticks_per_sec = tick_count / elapsed if elapsed > 0 else 0
        
        logger.info(f" Tick #{tick_count}: {tick.symbol} bid={tick.bid:.2f} ask={tick.ask:.2f} spread={tick.spread:.2f} ({ticks_per_sec:.1f} ticks/s)")
    
    def on_connected():
        logger.info(" MT5 CONECTADO!")
    
    def on_disconnected():
        logger.warning(" MT5 DESCONECTADO")
    
    def on_error(error):
        logger.error(f" Erro: {error}")
    
    bridge.register_callbacks(
        on_tick=on_tick,
        on_connected=on_connected,
        on_disconnected=on_disconnected,
        on_error=on_error
    )
    
    # Iniciar bridge
    logger.info("Iniciando TCP socket server...")
    bridge.start()
    
    # Aguardar conexo do MT5
    print()
    print("Aguardando conexo do MT5...")
    print("O EA deve conectar automaticamente quando iniciar")
    print()
    
    timeout = 60  # 60 segundos
    start = time.time()
    
    while not bridge.is_connected():
        elapsed = time.time() - start
        print(f"\rAguardando... {elapsed:.0f}s / {timeout}s", end="", flush=True)
        
        if elapsed >= timeout:
            print("\n\n Timeout: MT5 no conectou dentro do tempo limite")
            print("\nVerifique:")
            print("1. MT5 est rodando?")
            print("2. EA est anexado ao grfico?")
            print("3. EA est configurado com host=127.0.0.1, port=5555?")
            print("4. Firewall no est bloqueando a porta 5555?")
            bridge.stop()
            return
        
        time.sleep(1)
    
    print("\n\n MT5 Conectado!")
    
    # Rodar por 60 segundos
    print()
    print("Monitorando comunicao por 60 segundos...")
    print("Pressione Ctrl+C para parar")
    print()
    
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\nTeste interrompido pelo usurio")
    
    # Estatsticas
    stats = bridge.get_stats()
    
    print()
    print("=" * 80)
    print("RESUMO DO TESTE REAL")
    print("=" * 80)
    print(f"Tempo rodando: {stats.get('uptime_seconds', 0):.0f}s")
    print(f"Ticks recebidos: {stats['ticks_received']}")
    print(f"Sinais enviados: {stats['signals_sent']}")
    print(f"Erros: {stats['errors']}")
    print(f"Reconexes: {stats['reconnections']}")
    print(f"Latncia mdia: {stats['avg_latency_ms']:.2f}ms")
    
    ticks_per_sec = stats['ticks_received'] / stats.get('uptime_seconds', 1)
    print(f"Ticks por segundo: {ticks_per_sec:.1f}")
    
    if stats['ticks_received'] > 0 and stats['errors'] < 5:
        print("\n TESTE REAL PASSOU COM SUCESSO!")
        print("O sistema est pronto para live trading!")
    else:
        print("\n TESTE COM PROBLEMAS")
        print("Verifique os logs em logs/live_trading.log")
    
    print("=" * 80)
    
    # Parar bridge
    bridge.stop()


def main():
    parser = argparse.ArgumentParser(description="Teste de comunicao MT5 <-> Python")
    parser.add_argument("--mode", choices=["simulated", "real"], default="simulated",
                       help="Modo de teste: simulated (sem MT5) ou real (com MT5)")
    
    args = parser.parse_args()
    
    setup_basic_logging()
    
    if args.mode == "simulated":
        test_simulated()
    else:
        test_real()


if __name__ == "__main__":
    main()




