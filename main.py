from src.catho import Catho

c = Catho()
c.login()
c.buscar_vagas(termo_busca="python", local="sao paulo sp")
res = c.realizar_candidaturas(max_pages=10, blacklist_empresas=["BAIRESDEV"])
c.driver.close()
