import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import mercadopago
from supabase import create_client, Client
import boto3
from botocore.config import Config

# --- CONFIGURAÇÕES DE API E CREDENCIAIS ---
# Access Token de Produção oficial ativado no Mercado Pago:
MP_ACCESS_TOKEN = "APP_USR-1897163864153890-072301-0fb233e4976a8c3a845c136798f3bb06-1764155532"

SUPABASE_URL = "https://ypfqoubipzrfnvtkphoe.supabase.co"
SUPABASE_KEY = "sb_publishable_mOKdiwXupg6-RFLzbPJg1Q_Br32NkPD"

R2_ACCOUNT_ID = "fd153f4bb2027eaf223badad9c54adf9"
R2_ACCESS_KEY_ID = "0b51bc8855126f4498d4ba6d54434544"
R2_SECRET_ACCESS_KEY = "63f0f08d4f1f7b42ce9f1237d68b8d62b40ab69ab9fc5fc1837f553d367e8e06"
R2_BUCKET_NAME = "replay-sinuca-videos"

# --- INICIALIZAÇÃO DA APLICAÇÃO E SERVIÇOS ---
APP_VERSION = "v1.0.1"

app = FastAPI(title="Sistema Replay Sinuca", version=APP_VERSION)

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

s3_client = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
)

class ReplayRequest(BaseModel):
    mesa_id: str
    evento: Optional[str] = "replay_request"

class CriarPedidoRequest(BaseModel):
    video_ids: List[str]

@app.get("/", response_class=HTMLResponse)
def pagina_principal():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Replay Sinuca - Mesa 01</title>
        <style>
            * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; padding-bottom: 100px; }
            .container { max-width: 600px; margin: 0 auto; }
            .header { text-align: center; padding: 20px 0; border-bottom: 1px solid #334155; }
            .header h1 { margin: 0; color: #38bdf8; font-size: 24px; display: flex; align-items: center; justify-content: center; gap: 8px; }
            .header p { color: #94a3b8; font-size: 14px; margin-top: 5px; }
            .badge-version { background-color: #334155; color: #38bdf8; border: 1px solid #0284c7; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: bold; }
            
            .video-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 15px; margin: 15px 0; display: flex; align-items: center; justify-content: space-between; }
            .video-info { display: flex; align-items: center; gap: 12px; }
            .video-info input[type="checkbox"] { width: 20px; height: 20px; accent-color: #22c55e; cursor: pointer; }
            .video-details strong { display: block; color: #f1f5f9; font-size: 16px; }
            .video-details span { color: #64748b; font-size: 12px; }
            .price-tag { background-color: #0284c7; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 14px; }
            
            .checkout-bar { position: fixed; bottom: 0; left: 0; right: 0; background-color: #0f172a; border-top: 1px solid #334155; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; max-width: 600px; margin: 0 auto; }
            .checkout-info { font-size: 14px; color: #cbd5e1; }
            .checkout-info strong { color: #22c55e; font-size: 18px; }
            
            .btn-pix { background-color: #22c55e; color: #052e16; font-weight: bold; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; transition: background 0.2s; }
            .btn-pix:hover { background-color: #16a34a; }
            .btn-simular { background-color: #3b82f6; color: white; border: none; padding: 10px 15px; border-radius: 6px; width: 100%; margin-top: 10px; cursor: pointer; font-weight: bold; }

            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); align-items: center; justify-content: center; z-index: 100; }
            .modal-content { background: #1e293b; padding: 25px; border-radius: 12px; max-width: 400px; width: 90%; text-align: center; }
            .modal-content img { max-width: 200px; margin: 15px 0; border-radius: 8px; }
            .pix-code { background: #0f172a; padding: 10px; border-radius: 6px; word-break: break-all; font-family: monospace; font-size: 11px; margin: 10px 0; color: #38bdf8; }
            .btn-close { background: #64748b; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-top: 10px; }
        </style>
    </head>
    <body>

        <div class="container">
            <div class="header">
                <h1>🎱 Replay Sinuca <span class="badge-version">v1.0.1</span></h1>
                <p>Mesa 01 - Selecione as suas jogadas e efetue o download</p>
                <button class="btn-simular" onclick="simularCliqueBotao()">🎮 Simular Pressionar de Botão (ESP32)</button>
            </div>

            <div id="lista-videos">
                <div class="video-card">
                    <div class="video-info">
                        <input type="checkbox" class="video-select" data-id="vid-demo-01" onchange="atualizarCarrinho()">
                        <div class="video-details">
                            <strong>📹 Tacada Especial - 21:15</strong>
                            <span>Duração: 20s • Alta Definição</span>
                        </div>
                    </div>
                    <span class="price-tag">R$ 1,00</span>
                </div>

                <div class="video-card">
                    <div class="video-info">
                        <input type="checkbox" class="video-select" data-id="vid-demo-02" onchange="atualizarCarrinho()">
                        <div class="video-details">
                            <strong>📹 Efeito Triplo - 21:32</strong>
                            <span>Duração: 20s • Alta Definição</span>
                        </div>
                    </div>
                    <span class="price-tag">R$ 1,00</span>
                </div>
            </div>
        </div>

        <div class="checkout-bar">
            <div class="checkout-info">
                Total: <strong id="total-txt">R$ 0,00</strong><br>
                <small><span id="qtd-txt">0</span> vídeo(s) selecionado(s)</small>
            </div>
            <button class="btn-pix" onclick="gerarPix()">Pagar via PIX</button>
        </div>

        <div id="modal-pix" class="modal">
            <div class="modal-content">
                <h3 style="margin-top:0; color:#22c55e;">Pagamento PIX Gerado!</h3>
                <p style="font-size:14px; color:#cbd5e1;">Pague através da sua aplicação bancária para libertar o acesso instantâneo:</p>
                <img id="qr-code-img" src="" alt="QR Code PIX">
                <div class="pix-code" id="pix-copia-cola"></div>
                <button class="btn-pix" style="width:100%; margin-top:10px;" onclick="copiarPix()">Copiar Código PIX</button>
                <button class="btn-close" onclick="fecharModal()">Fechar</button>
            </div>
        </div>

        <script>
            function atualizarCarrinho() {
                const selecionados = document.querySelectorAll('.video-select:checked');
                const qtd = selecionados.length;
                document.getElementById('qtd-txt').innerText = qtd;
                document.getElementById('total-txt').innerText = 'R$ ' + (qtd * 1.00).toFixed(2);
            }

            async function gerarPix() {
                const selecionados = document.querySelectorAll('.video-select:checked');
                const ids = Array.from(selecionados).map(cb => cb.getAttribute('data-id'));

                if (ids.length === 0) {
                    alert('Por favor, selecione pelo menos 1 vídeo para continuar!');
                    return;
                }

                try {
                    const response = await fetch('/api/pedidos/criar-pix', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ video_ids: ids })
                    });

                    const data = await response.json();

                    if (data.qr_code_base64) {
                        document.getElementById('qr-code-img').src = 'data:image/png;base64,' + data.qr_code_base64;
                        document.getElementById('pix-copia-cola').innerText = data.pix_copia_cola;
                        document.getElementById('modal-pix').style.display = 'flex';
                    } else {
                        alert('Erro ao gerar PIX: ' + (data.detail || 'Tente novamente.'));
                    }
                } catch (err) {
                    alert('Erro na ligação com o servidor!');
                }
            }

            function copiarPix() {
                const codigo = document.getElementById('pix-copia-cola').innerText;
                navigator.clipboard.writeText(codigo);
                alert('Código PIX copiado para a área de transferência!');
            }

            function fecharModal() {
                document.getElementById('modal-pix').style.display = 'none';
            }

            async function simularCliqueBotao() {
                const res = await fetch('/api/solicitar-replay', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mesa_id: 'mesa_01', evento: 'replay_request' })
                });
                const data = await res.json();
                alert('Sinal do botão processado com sucesso! ' + JSON.stringify(data));
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/solicitar-replay")
def solicitar_replay(payload: ReplayRequest):
    try:
        resposta = supabase.table("videos").insert({
            "mesa_id": payload.mesa_id,
            "url_video": f"https://{R2_BUCKET_NAME}.r2.cloudflarestorage.com/exemplo_video.mp4",
            "status_pago": False
        }).execute()

        return {
            "status": "sucesso",
            "mensagem": "Solicitação de Replay registada com sucesso!",
            "dados": resposta.data
        }
    except Exception as e:
        return {"status": "erro", "detalhes": str(e)}


@app.post("/api/pedidos/criar-pix")
def criar_pedido_pix(payload: CriarPedidoRequest):
    quantidade = len(payload.video_ids)
    if quantidade == 0:
        raise HTTPException(status_code=400, detail="Nenhum vídeo selecionado")

    valor_total = float(quantidade * 1.00)

    payment_data = {
        "transaction_amount": valor_total,
        "description": f"Download de {quantidade} vídeo(s) de Replay - Sinuca",
        "payment_method_id": "pix",
        "payer": {
            "email": "cliente.replay.sinuca@gmail.com",
            "first_name": "Cliente",
            "last_name": "Sinuca"
        }
    }

    try:
        result = sdk.payment().create(payment_data)
        payment = result.get("response", {})

        if "point_of_interaction" in payment:
            transaction_data = payment["point_of_interaction"]["transaction_data"]
            return {
                "pedido_id": payment.get("id"),
                "valor_total": valor_total,
                "quantidade_videos": quantidade,
                "pix_copia_cola": transaction_data.get("qr_code"),
                "qr_code_base64": transaction_data.get("qr_code_base64")
            }
        else:
            msg_erro = payment.get("message", "Erro desconhecido")
            raise HTTPException(status_code=500, detail=f"Erro Mercado Pago: {msg_erro}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.post("/api/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    try:
        data = await request.json()
        if data.get("action") == "payment.updated":
            payment_id = data["data"]["id"]
            payment_info = sdk.payment().get(payment_id)["response"]

            if payment_info.get("status") == "approved":
                print(f"✅ Pagamento {payment_id} aprovado com sucesso!")

        return JSONResponse(content={"status": "ok"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)


if __name__ == "__main__":
    print("🚀 Servidor Replay Sinuca a iniciar em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
