import os
from urllib.parse import parse_qs

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class Catho:
    def __init__(self) -> None:
        self.PREFIX = "CATHO"
        self.USERNAME = None
        self.PWD = None
        self.URL = None
        self.LOGIN_URL = None

        self.get_credentials_from_env()

        self.driver = webdriver.Firefox()

    def get_credentials_from_env(self):
        load_dotenv(".env")
        for attr in ("USERNAME", "PWD", "URL", "LOGIN_URL"):
            key = f"{self.PREFIX}_{attr}"
            if not os.environ.get(key):
                raise ValueError(f"{key} não encontrado no ambiente")
            setattr(self, attr, os.environ.get(key))

    def login(self):
        self.driver.get(self.LOGIN_URL)
        self.driver.find_element(By.XPATH, "//input[@type='email']").send_keys(
            self.USERNAME
        )
        self.driver.find_element(
            By.XPATH, "//input[@type='password']"
        ).send_keys(self.PWD, Keys.ENTER)
        # wait for redirect to finish login proccess
        WebDriverWait(driver=self.driver, timeout=10).until(
            EC.url_to_be(f"{self.URL}/area-candidato")
        )

    def buscar_vagas(self, termo_busca: str, **kwargs):
        url = f"{self.URL}/vagas/?q={termo_busca}"
        if kwargs.get("local"):
            url = f"{self.URL}/vagas/{termo_busca}/{kwargs.get('local')}"
        self.driver.get(url.replace(" ", "-").lower())
        try:
            self.__fechar_banner()
        except NoSuchElementException:
            pass

    def __fechar_banner(self):
        self.driver.find_element(
            By.CLASS_NAME, "container-close-app-banner"
        ).click()

    def realizar_candidaturas(
        self, max_pages: int = 3, blacklist_empresas: list[str] | None = None
    ):
        candidaturas = []
        total_pages = self.__get_num_pages()
        if total_pages < max_pages:
            max_pages = total_pages
        for page in range(1, max_pages + 1):
            lista_vagas = self.__get_lista_vagas()
            if not lista_vagas:
                print("LISTA DE VAGAS NÃO ENCONTRADA")
                return None
            # xpath is 1 indexed
            for idx_vaga in range(1, len(lista_vagas) + 1):
                infos_vaga = self.__get_infos_vaga(idx_vaga)
                if infos_vaga["empresa"] in blacklist_empresas:
                    continue
                if self.__ja_candidatado(idx_vaga):
                    continue
                print(
                    f"{infos_vaga['empresa']} | ",
                    f"{infos_vaga['titulo']} | ",
                    end="",
                )
                infos_vaga["candidatado"] = self.candidatar(idx_vaga)
                candidaturas.append(infos_vaga)
                self.__fechar_snack_bar()
                if infos_vaga["candidatado"] is True:
                    print("OK")
                else:
                    print("CANCELADO")
            self.__go_to_page(page_num=page + 1)
        return candidaturas

    def __ja_candidatado(self, idx_vaga: int):
        xpath = (
            f"//li[{idx_vaga}]/descendant::div[text()='Candidatura Iniciada'] |"
            f"//li[{idx_vaga}]/descendant::div[text()='Currículo já enviado']"
        )
        try:
            self.driver.find_element(By.XPATH, xpath)
            return True
        except Exception:
            return False

    def candidatar(self, idx_vaga: int):
        btn = self.__get_apply_btn(idx_vaga)
        if btn is None:
            return False
        btn.click()
        if btn.text == "Quero me candidatar":
            self.__handle_modal()
        # se houver questionario para a vaga, cancelar
        if self.__fechar_questionario():
            return False
        return True

    def __get_num_pages(self):
        xpath = "//nav/a[contains(@class, 'PageButton')]"
        btns = self.driver.find_elements(By.XPATH, xpath)
        return int(btns[-1].text)

    def __get_lista_vagas(self):
        xpath = "/html/body/div[1]/div[4]/main/div[3]/div/div/section/ul/li"
        return self.driver.find_elements(By.XPATH, xpath)

    def __get_empresa(self, idx: int):
        xpath = f"//li[{idx}]/article/article/header/div/p"
        return self.driver.find_element(By.XPATH, xpath).text.replace(
            "Por que?", ""
        )

    def __get_titulo(self, idx: WebElement):
        xpath = f"//li[{idx}]/article/article/header/div/div[1]/h2/a"
        return self.driver.find_element(By.XPATH, xpath).text

    def __get_infos_vaga(self, idx_vaga: int):
        return {
            "empresa": self.__get_empresa(idx_vaga),
            "titulo": self.__get_titulo(idx_vaga),
        }

    def __get_apply_btn(self, idx: WebElement):
        xpath = (
            f'//li[{idx}]/descendant::button[text()="Quero me candidatar"] |'
            f'//li[{idx}]/descendant::button[text()="Enviar Candidatura Fácil"]'
        )
        try:
            return self.driver.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            return None

    def __handle_modal(self):
        modal_btn_xpath = "/html/body/section/div/article/div/form/button"
        # wait for modal to open
        WebDriverWait(driver=self.driver, timeout=10).until(
            EC.element_to_be_clickable((By.XPATH, modal_btn_xpath))
        )
        self.driver.find_element(By.XPATH, modal_btn_xpath).click()
        # close msg
        msg_btn_xpath = "/html/body/section[2]/div/article/footer/button"
        WebDriverWait(driver=self.driver, timeout=10).until(
            EC.element_to_be_clickable((By.XPATH, msg_btn_xpath))
        )
        self.driver.find_element(By.XPATH, msg_btn_xpath).click()

    def __go_to_page(self, page_num: int):
        if "?" in self.driver.current_url:
            url, query = self.driver.current_url.split(sep="?", maxsplit=2)
        else:
            url = self.driver.current_url
            query = ""
        query = self.__update_query_page(query_str=query, page_num=page_num)
        self.driver.get(f"{url}?{query}")

    def __update_query_page(self, query_str: str, page_num: int):
        query_dict = parse_qs(query_str)
        query_dict["page"] = [page_num]
        res = "&".join([f"{key}={val[0]}" for key, val in query_dict.items()])
        return res

    def __fechar_snack_bar(self):
        # wait for msg to appear
        bar_xpath = "//div[contains(@class, 'SnackBar__SnackBarDialog')]"
        try:
            WebDriverWait(driver=self.driver, timeout=2).until(
                EC.visibility_of_element_located((By.XPATH, bar_xpath))
            )
        except Exception:
            return None
        # close msg
        btn_xpath = "//button[contains(@class, 'SnackBar__CloseButton')]"
        WebDriverWait(driver=self.driver, timeout=5).until(
            EC.element_to_be_clickable((By.XPATH, btn_xpath))
        )
        self.driver.find_element(By.XPATH, btn_xpath).click()

    def __fechar_questionario(self):
        header_xpath = '//header/div/h2[text()="Questionário da vaga"]'
        try:
            WebDriverWait(driver=self.driver, timeout=5).until(
                EC.visibility_of_element_located((By.XPATH, header_xpath))
            )
        except Exception:
            return False
        btn_xpath = "//article/button[contains(@class, 'Modal__CloseIcon')]"
        WebDriverWait(driver=self.driver, timeout=5).until(
            EC.element_to_be_clickable((By.XPATH, btn_xpath))
        )
        self.driver.find_element(By.XPATH, btn_xpath).click()
        return True
