import os
import uvicorn
from datetime import datetime
import zoneinfo
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import mercadopago
from supabase import create_client, Client
import boto3
from botocore.config import Config

# --- CONFIGURAÇÕES DE API E CREDENCIAIS ---
MP_ACCESS_TOKEN = "APP_USR-1897163864153890-072301-0fb233e4976a8c3a845c136798f3bb06-1764155532"

SUPABASE_URL = "https://ypfqoubipzrfnvtkphoe.supabase.co"
SUPABASE_KEY = "sb_publishable_mOKdiwXupg6-RFLzbPJg1Q_Br32NkPD"

# Chaves Cloudflare R2 (Token: python-replay)
R2_ACCOUNT_ID = "fd153f4bb2027eaf223badad9c54adf9"
R2_ACCESS_KEY_ID = "0d28307d8f9390fb14595b1ae6202ea4"
R2_SECRET_ACCESS_KEY = "bbd7b9a060c3acd8b1d883eaa3686ddc0c618109e8a04ed64318b4c4bd4c2761"
R2_BUCKET_NAME = "replay-sinuca-videos"
R2_PUBLIC_URL_BASE = "https://pub-34bf950fa2a14cd2ac1117f8db326779.r2.dev"

# --- INICIALIZAÇÃO DA APLICAÇÃO E SERVIÇOS ---
APP_VERSION = "v1.2.1"

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
    video_ids: List[int]

@app.get("/", response_class=HTMLResponse)
def pagina_principal():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Replay Sinuca - Mesa 01</title>
        <style>
            * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; padding-bottom: 120px; }
            .container { max-width: 600px; margin: 0 auto; }
            .header { text-align: center; padding: 20px 0; border-bottom: 1px solid #334155; }
            .header h1 { margin: 0; color: #38bdf8; font-size: 24px; display: flex; align-items: center; justify-content: center; gap: 8px; }
            .header p { color: #94a3b8; font-size: 14px; margin-top: 5px; }
            .badge-version { background-color: #334155; color: #38bdf8; border: 1px solid #0284c7; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: bold; }
            
            .video-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 15px; margin: 15px 0; display: flex; align-items: center; justify-content: space-between; }
            .video-info { display: flex; align-items: center; gap: 12px; }
            .video-info input[type="checkbox"] { width: 22px; height: 22px; accent-color: #22c55e; cursor: pointer; }
            .video-details strong { display: block; color: #f1f5f9; font-size: 15px; }
            .video-details .time-badge { color: #38bdf8; font-weight: bold; font-size: 13px; }
            .video-details .status-txt { display: block; color: #64748b; font-size: 12px; margin-top: 3px; }
            .price-tag { background-color: #0284c7; color: white; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; }
            .btn-download { background-color: #22c55e; color: #052e16; padding: 8px 16px; border-radius: 20px; font-weight: bold; text-decoration: none; font-size: 14px; }
            
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
    <body onload="carregarVideos()">

        <div class="container">
            <div class="header">
                <h1>🎱 Replay Sinuca <span class="badge-version">v1.2.1</span></h1>
                <p>Mesa 01 - Selecione a jogada pela data e horário</p>
                <button class="btn-simular" onclick="simularCliqueBotao()">🎮 Simular Pressionar de Botão (ESP32)</button>
            </div>

            <div id="lista-videos">
                <p style="text-align:center; color:#94a3b8; margin-top:30px;">Carregando jogadas recentes...</p>
            </div>
        </div>

        <div class="checkout-bar">
            <div class="checkout-info">
                Total: <strong id="total-txt">R$ 0,00</strong><br>
                <small><span id="qtd-txt">0</span> vídeo(s) selecionado(s)</small>
            </div>
            <button class="btn-pix" onclick="gerarPix()">Pagar via PIX (R$ 1,00)</button>
        </div>

        <div id="modal-pix" class="modal">
            <div class="modal-content">
                <h3 style="margin-top:0; color:#22c55e;">Pagamento PIX Gerado!</h3>
                <p style="font-size:14px; color:#cbd5e1;">Pague com o aplicativo do seu banco para liberar o download instantâneo:</p>
                <img id="qr-code-img" src="" alt="QR Code PIX">
                <div class="pix-code" id="pix-copia-cola"></div>
                <button class="btn-pix" style="width:100%; margin-top:10px;" onclick="copiarPix()">Copiar Código PIX</button>
                <button class="btn-close" onclick="fecharModal()">Fechar</button>
            </div>
        </div>

        <script>
            let intervalVerificacao = null;

            function formatarDataHora(item) {
                const rawDate = item.data_hora || item.created_at || item.criado_em;
                if (!rawDate) return "ID #" + item.id;
                
                try {
                    const d = new Date(rawDate);
                    if (isNaN(d.getTime())) return "ID #" + item.id;
                    
                    const dataStr = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
                    const horaStr = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    
                    return `${dataStr} às ${horaStr}`;
                } catch(e) {
                    return "ID #" + item.id;
                }
            }

            async function carregarVideos() {
                try {
                    const res = await fetch('/api/videos/recentes');
                    const data = await res.json();
                    const container = document.getElementById('lista-videos');
                    
                    if (!data.videos || data.videos.length === 0) {
                        container.innerHTML = '<p style="text-align:center; color:#94a3b8; margin-top:30px;">Nenhum replay recente gravado ainda. Aperte o botão da mesa!</p>';
                        return;
                    }

                    container.innerHTML = '';
                    data.videos.forEach(v => {
                        const dataHoraStr = formatarDataHora(v);
                        const mesaLimpa = (v.mesa_id || '01').replace('mesa_', '');

                        let htmlCard = `
                            <div class="video-card">
                                <div class="video-info">
                                    ${v.status_pago ? '' : `<input type="checkbox" class="video-select" data-id="${v.id}" onchange="atualizarCarrinho()">`}
                                    <div class="video-details">
                                        <strong>📹 <span class="time-badge">${dataHoraStr}</span></strong>
                                        <span class="status-txt">Mesa ${mesaLimpa} • ${v.status_pago ? '✅ Liberado' : '🔒 Aguardando Pagamento'}</span>
                                    </div>
                                </div>
                                ${v.status_pago ? `<a href="${v.url_video}" target="_blank" class="btn-download">⬇️ Baixar Vídeo</a>` : '<span class="price-tag">R$ 1,00</span>'}
                            </div>
                        `;
                        container.innerHTML += htmlCard;
                    });
                } catch(e) {
                    console.error("Erro ao carregar vídeos:", e);
                }
            }

            function atualizarCarrinho() {
                const selecionados = document.querySelectorAll('.video-select:checked');
                const qtd = selecionados.length;
                document.getElementById('qtd-txt').innerText = qtd;
                document.getElementById('total-txt').innerText = 'R$ ' + (qtd * 1.00).toFixed(2);
            }

            async function gerarPix() {
                const selecionados = document.querySelectorAll('.video-select:checked');
                const ids = Array.from(selecionados).map(cb => parseInt(cb.getAttribute('data-id')));

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

                        if (intervalVerificacao) clearInterval(intervalVerificacao);
                        intervalVerificacao = setInterval(carregarVideos, 3000);

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
                if (intervalVerificacao) clearInterval(intervalVerificacao);
                carregarVideos();
            }

            async function simularCliqueBotao() {
                const res = await fetch('/api/solicitar-replay', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mesa_id: '01', evento: 'replay_request' })
                });
                const data = await res.json();
                alert('Sinal do botão processado! Replay adicionado.');
                carregarVideos();
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/videos/recentes")
def listar_videos_recentes():
    try:
        resposta = supabase.table("videos").select("*").order("id", desc=True).limit(15).execute()
        return {"videos": resposta.data}
    except Exception as e:
        return {"videos": [], "erro": str(e)}


@app.post("/api/solicitar-replay")
def solicitar_replay(payload: ReplayRequest):
    try:
        agora_sp = datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).isoformat()
        mesa_limpa = payload.mesa_id.replace("mesa_", "")
        
        # Define a URL do arquivo no Cloudflare R2
        url_video = f"{R2_PUBLIC_URL_BASE}/replay_mesa_{mesa_limpa}_exemplo.mp4"

        resposta = supabase.table("videos").insert({
            "mesa_id": mesa_limpa,
            "url_video": url_video,
            "status_pago": False,
            "data_hora": agora_sp
        }).execute()

        novo_id = resposta.data[0]["id"]

        return {
            "status": "sucesso",
            "mensagem": "Solicitação registrada com sucesso!",
            "id_video": novo_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pedidos/criar-pix")
def criar_pedido_pix(payload: CriarPedidoRequest):
    quantidade = len(payload.video_ids)
    if quantidade == 0:
        raise HTTPException(status_code=400, detail="Nenhum vídeo selecionado")

    valor_total = float(quantidade * 1.00)
    ids_str = ",".join(map(str, payload.video_ids))

    payment_data = {
        "transaction_amount": valor_total,
        "description": f"Download de {quantidade} vídeo(s) de Replay - Sinuca",
        "payment_method_id": "pix",
        "external_reference": ids_str,
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
        payment_id = None
        if data.get("type") == "payment":
            payment_id = data.get("data", {}).get("id")
        elif data.get("action") == "payment.updated":
            payment_id = data.get("data", {}).get("id")

        if payment_id:
            payment_info = sdk.payment().get(payment_id)["response"]

            if payment_info.get("status") == "approved":
                ref_ids = payment_info.get("external_reference")
                print(f"✅ Pagamento {payment_id} aprovado para os vídeos: {ref_ids}")

                if ref_ids:
                    lista_ids = [int(i.strip()) for i in ref_ids.split(",") if i.strip().isdigit()]
                    for vid_id in lista_ids:
                        supabase.table("videos").update({"status_pago": True}).eq("id", vid_id).execute()
                        print(f"🔓 Vídeo #{vid_id} liberado no Supabase!")

        return JSONResponse(content={"status": "ok"}, status_code=200)
    except Exception as e:
        print(f"❌ Erro Webhook: {e}")
        return JSONResponse(content={"erro": str(e)}, status_code=500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Servidor Replay Sinuca a iniciar na porta {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
