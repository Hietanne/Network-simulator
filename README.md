# Verkkosimulaattori – GUI

Graafinen Python-sovellus yksinkertaisten verkkojen (reitittimet, tietokoneet, linkit) simuloimiseen ja havainnollistamiseen.

Sovelluksella voit rakentaa oman topologian, säätää linkkien viiveitä ja pakettihäviöitä, lähettää viestejä pisteestä A pisteeseen B ja seurata, miten paketit kulkevat (tai katoavat) verkossa. Lisäksi viimeisin reitti korostetaan graafissa, ja pakettien viiveistä lasketaan tilastoja.

---

## Ominaisuudet

- **Graafinen käyttöliittymä (Tkinter + matplotlib)**
  - Verkon topologia piirretään ikkunaan.
  - Viimeisin toteutunut reitti korostetaan punaisella.
- **Laitteet (solmut)**
  - Lisää / poista laitteita.
  - Muokkaa laitteen tyyppiä: `reititin` tai `tietokone`.
  - Tyyppi vaikuttaa solmun väriin (esim. reititin vs. päätelaite).
- **Yhteydet (linkit)**
  - Lisää / poista yhteyksiä kahden laitteen välille.
  - Aseta:
    - linkin viive (ms)
    - pakettihäviön todennäköisyys (%)
  - Muokkaa olemassa olevan linkin viivettä ja häviötä.
- **Simulaatio**
  - Lähetä viesti laitteen A ja laitteen B välillä.
  - Reitti lasketaan lyhyimmän polun algoritmilla (Dijkstra, painona viive).
  - Jokaisella linkillä:
    - jitter (satunnainen kerroin, esim. 0.8–1.2)
    - mahdollinen pakettihäviö (loss)
  - Jos paketti häviää jollakin linkillä, simulaatio virtaa siihen asti ja paketti merkitään epäonnistuneeksi.
- **Pakettiloki ja tilastot**
  - Sovellus tallentaa jokaisesta lähetyksestä:
    - ajan
    - lähettäjän ja vastaanottajan
    - suunnitellun reitin
    - toteutuneen reitin
    - kokonaisviiveen
    - onnistuiko vai ei, ja häviön syyn
  - Näe kaikki merkinnät pakettilokista.
  - Laske tilastoja:
    - lähetettyjen pakettien määrä
    - onnistuneet / epäonnistuneet
    - keskimääräinen viive
    - pienin / suurin viive
  - Mahdollisuus tyhjentää pakettiloki ja lokinäkymä.
- **Asetukset**
  - Jitter min/max (esim. 0.8–1.2).
  - Linkkikohtaisen siirron nukkumisaika (s/linkki), eli visuaalinen hidastus.
- **Topologian tallennus ja lataus**
  - Tallenna nykyinen verkko JSON-tiedostoon:
    - laitteet ja tyypit
    - yhteydet, viiveet ja häviöt
    - jitter- ja nukkumisaika-asetukset
  - Lataa topologia takaisin JSON-tiedostosta.
- **Esimerkkiverkko**
  - Napista "Luo esimerkkiverkko" saat valmiin topologian:
    - `PC_Helsinki -> Reititin_A -> Reititin_C -> Reititin_B -> Palvelin_Berlin`
    - sopivat esimerkkiviiveet.

---

## Vaatimukset

- **Python 3.8+**
- Seuraavat kirjastot (asennettavissa `pip`illä):
  - `networkx`
  - `matplotlib`

Tkinter tulee yleensä Pythonin mukana valmiina (Windows / useimmat Linux-jakelut).  
Jos saat virheen, joka liittyy Tkinteriin (`ModuleNotFoundError: No module named 'tkinter'`), asenna Tkinter erikseen jakelusi ohjeiden mukaan.

### Asennus

```bash
pip install networkx matplotlib