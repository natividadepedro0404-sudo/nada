import os
import time
import requests
import webbrowser
from threading import Timer
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from supabase import create_client, Client
from checker_service import DominosChecker
import checker_service

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configurações
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yyqvpykqoqiygdinbcbj.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl5cXZweWtxb3FpeWdkaW5iY2JqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI0MDQyNDIsImV4cCI6MjA4Nzk4MDI0Mn0.zfTy2x0mrj3j2TpMhKCz-P8QdnL3bw-V9zWKfwtQpYc")
MISTICPAY_CLIENT_ID = os.environ.get("MISTICPAY_CLIENT_ID", "ci_libdweclsjyry50")
MISTICPAY_CLIENT_SECRET = os.environ.get("MISTICPAY_CLIENT_SECRET", "cs_kknlfy76fe2ir4nqjydf8ebee")
MISTICPAY_API_URL = "https://api.misticpay.com/api"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DOMINOS_EMAIL = os.environ.get("DOMINOS_EMAIL", "p808409@gmail.com")
DOMINOS_PASSWORD = os.environ.get("DOMINOS_PASSWORD", "@P808409p10")

# Instanciando o checker (ele não abrirá o chrome até o primeiro uso)
checker_service.checker_instance = DominosChecker(DOMINOS_EMAIL, DOMINOS_PASSWORD)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session['user_id'] = response.user.id
        session['access_token'] = response.session.access_token
        return jsonify({"success": True, "message": "Login successful"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            profiles = supabase.table('profiles').select('*').eq('id', response.user.id).execute()
            if not profiles.data:
                supabase.table('profiles').insert({"id": response.user.id, "balance": 0.0, "email": email}).execute()
        return jsonify({"success": True, "message": "Registro realizado com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logout"})

@app.route('/api/user/balance', methods=['GET'])
def get_balance():
    if 'user_id' not in session: return jsonify({"success": False, "message": "Nao autorizado"}), 401
    
    try:
        user_id = session['user_id']
        response = supabase.table('profiles').select('balance').eq('id', user_id).execute()
        if response.data:
            return jsonify({"success": True, "balance": response.data[0]['balance']})
        return jsonify({"success": False, "message": "Perfil não encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/deposit', methods=['POST'])
def create_deposit():
    if 'user_id' not in session: return jsonify({"success": False, "message": "Nao autorizado"}), 401
        
    data = request.json
    amount = float(data.get('amount', 0))
    if amount < 10 or amount > 300:
        return jsonify({"success": False, "message": "Valor deve ser entre 10 e 300 reais"}), 400
        
    user_id = session['user_id']
    
    try:
        headers = {
            "ci": MISTICPAY_CLIENT_ID,
            "cs": MISTICPAY_CLIENT_SECRET,
            "Content-Type": "application/json"
        }
        
        transaction_id = f"CC{int(time.time())}{user_id[:4]}"
        
        payload = {
            "amount": amount,
            "payerName": "Cliente CC Checker",
            "payerDocument": "00000000000",
            "transactionId": transaction_id,
            "description": "Adicionar Saldo",
            "projectWebhook": os.environ.get("WEBHOOK_URL", "https://checker-db9i.onrender.com/api/webhook/misticpay")
        }
        
        url = f"{MISTICPAY_API_URL}/transactions/create"
        res = requests.post(url, json=payload, headers=headers)
        
        if res.status_code not in [200, 201]:
            return jsonify({"success": False, "message": f"Erro Misticpay: {res.text}"}), 400
            
        response_data = res.json()
        
        # Debug: log da resposta para ajudar a identificar a estrutura
        print(f"[DEBUG] Misticpay Response: {response_data}")
        
        # Extrair dados da resposta corretamente
        mistic_data = response_data.get('data', response_data)
        
        # PIX Copia e Cola - procurar pelas chaves conhecidas
        pix_code = (
            mistic_data.get('copyPaste') or 
            mistic_data.get('pixCopiaECola') or 
            mistic_data.get('pix') or
            mistic_data.get('qrCode') or 
            mistic_data.get('pixCode', '')
        )
        
        # QR Code - extrair a URL ou gerar a partir do PIX
        qr_code_url = (
            mistic_data.get('qrcodeUrl') or 
            mistic_data.get('qrCodeUrl') or 
            mistic_data.get('qrcodeImage', '')
        )
        
        # Se temos o PIX mas não temos QR code URL, gerar um
        if pix_code and not qr_code_url:
            qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={pix_code}"
        
        # Se não temos PIX, retornar erro
        if not pix_code:
            return jsonify({"success": False, "message": "PIX não gerado pela Misticpay. Verifique as credenciais."}), 400
        
        db_id = mistic_data.get('transactionId', transaction_id)
        
        # Save to Supabase payments table
        payment_data = {
            "user_id": user_id,
            "amount": amount,
            "status": "pending",
            "misticpay_id": db_id,
            "pix_id": pix_code,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table('payments').insert(payment_data).execute()
        
        return jsonify({
            "success": True, 
            "message": "PIX gerado com sucesso!",
            "pix_code": pix_code,
            "qr_code_url": qr_code_url,
            "transaction_id": db_id,
            "amount": amount
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Endpoint to mock a webhook approval for local testing without real payments
@app.route('/api/deposit/dev-approve', methods=['POST'])
def dev_approve_deposit():
    if 'user_id' not in session: return jsonify({"error": "unauth"}), 401
    
    user_id = session['user_id']
    amount = float(request.json.get('amount', 0))
    
    try:
        curr_profile = supabase.table('profiles').select('balance').eq('id', user_id).execute().data[0]
        new_balance = float(curr_profile['balance']) + amount
        supabase.table('profiles').update({'balance': new_balance}).eq('id', user_id).execute()
        return jsonify({"success": True, "message": "Pagamento aprovado e saldo atualizado!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/webhook/misticpay', methods=['POST'])
def handle_misticpay_webhook():
    try:
        webhook_data = request.json
        transaction_id = webhook_data.get('transactionId')
        status = webhook_data.get('status')
        value = webhook_data.get('value', 0)
        
        print(f"[WEBHOOK] Recebido: transactionId={transaction_id}, status={status}, value={value}")
        
        if not transaction_id or not status:
            print("[WEBHOOK] Dados inválidos recebidos")
            return jsonify({"success": False, "message": "Dados inválidos"}), 400
        
        # Buscar o pagamento no banco
        payment = supabase.table('payments').select('*').eq('misticpay_id', str(transaction_id)).execute()
        
        if not payment.data:
            # Tentar buscar pelo pix_id também
            payment = supabase.table('payments').select('*').eq('pix_id', str(transaction_id)).execute()
        
        if not payment.data:
            print(f"[WEBHOOK] Pagamento não encontrado para transaction_id: {transaction_id}")
            return jsonify({"success": False, "message": "Pagamento não encontrado"}), 404
        
        payment_record = payment.data[0]
        user_id = payment_record['user_id']
        amount = payment_record['amount']
        
        print(f"[WEBHOOK] Pagamento encontrado: user_id={user_id}, amount={amount}")
        
        if status == "COMPLETO":
            # Atualizar status do pagamento
            supabase.table('payments').update({
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', payment_record['id']).execute()
            
            # Atualizar saldo do usuário
            profile = supabase.table('profiles').select('balance').eq('id', user_id).execute()
            if profile.data:
                current_balance = float(profile.data[0]['balance'])
                new_balance = current_balance + amount
                supabase.table('profiles').update({'balance': new_balance}).eq('id', user_id).execute()
                print(f"[WEBHOOK] Saldo atualizado: {current_balance} -> {new_balance}")
            
            return jsonify({"success": True, "message": "Pagamento processado com sucesso"}), 200
        elif status == "FALHA":
            # Marcar como falha
            supabase.table('payments').update({
                'status': 'failed',
                'failed_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', payment_record['id']).execute()
            print(f"[WEBHOOK] Pagamento marcado como falha")
            return jsonify({"success": True, "message": "Pagamento falhou"}), 200
        else:
            # Outros status
            print(f"[WEBHOOK] Status {status} recebido, apenas acknowlegding")
            return jsonify({"success": True, "message": f"Status atualizado: {status}"}), 200
            
    except Exception as e:
        print(f"[WEBHOOK] Erro: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/check_card', methods=['POST'])
def check_card():
    if 'user_id' not in session: return jsonify({"success": False, "message": "Nao autorizado"}), 401

    data = request.json
    card_line = data.get('card', '')
    
    if not card_line:
        return jsonify({"success": False, "message": "Cartão inválido", "status": "DIE"}), 400

    user_id = session['user_id']
    
    try:
        profile = supabase.table('profiles').select('balance').eq('id', user_id).execute().data[0]
        balance = float(profile['balance'])
        
        if balance <= 1.0:
            return jsonify({"success": False, "message": "Saldo insuficiente (Mínimo R$ 1.00 para checar)", "status": "DIE"}), 403
            
        result = checker_service.checker_instance.test_card(card_line)
        
        if "ERROR" in result:
            return jsonify({"success": False, "message": result, "status": "DIE"}), 500
            
        if result == "LIVE":
            new_balance = balance - 1.0
            supabase.table('profiles').update({'balance': new_balance}).eq('id', user_id).execute()
            
        return jsonify({"success": True, "status": result, "message": "Verificado com sucesso"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "status": "DIE"}), 500

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
