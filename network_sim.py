import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import random
from datetime import datetime
import json


class Verkkosimulaattori:
    """Verkon logiikka: laitteet, yhteydet ja viestien reititys."""

    def __init__(self, jitter_min=0.8, jitter_max=1.2, nukkumisaika=0.0):
        self.verkko = nx.Graph()
        self.jitter_min = float(jitter_min)
        self.jitter_max = float(jitter_max)
        self.nukkumisaika = float(nukkumisaika)
        self.pakettiloki = []
        self._pos_cache = None

    # --- Sisäiset apurit ---

    def _paivita_pos_cache(self):
        if len(self.verkko.nodes) == 0:
            self._pos_cache = {}
        else:
            self._pos_cache = nx.spring_layout(self.verkko)

    # --- Perusoperaatiot: laitteet ja yhteydet ---

    def lisaa_laite(self, nimi, tyyppi="reititin"):
        if not nimi:
            raise ValueError("Laitteen nimi ei voi olla tyhjä.")
        if nimi in self.verkko:
            raise ValueError(f"Laite '{nimi}' on jo olemassa.")
        vari = "lightgreen" if tyyppi == "tietokone" else "lightblue"
        self.verkko.add_node(nimi, tyyppi=tyyppi, color=vari)
        self._paivita_pos_cache()

    def muokkaa_laitetta(self, nimi, uusi_tyyppi):
        if nimi not in self.verkko:
            raise ValueError(f"Laitetta '{nimi}' ei löydy.")
        vari = "lightgreen" if uusi_tyyppi == "tietokone" else "lightblue"
        self.verkko.nodes[nimi]["tyyppi"] = uusi_tyyppi
        self.verkko.nodes[nimi]["color"] = vari

    def poista_laite(self, nimi):
        if nimi not in self.verkko:
            raise ValueError(f"Laitetta '{nimi}' ei löydy.")
        self.verkko.remove_node(nimi)
        self._paivita_pos_cache()

    def lisaa_yhteys(self, laite1, laite2, viive_ms=10.0, loss=0.0):
        if laite1 == laite2:
            raise ValueError("Laite ei voi olla yhteydessä itseensä.")
        if laite1 not in self.verkko or laite2 not in self.verkko:
            raise ValueError("Molempien laitteiden täytyy olla olemassa ennen yhteyden luontia.")
        loss = float(loss)
        if loss < 0.0 or loss > 1.0:
            raise ValueError("Häviön on oltava välillä 0.0 - 1.0.")
        self.verkko.add_edge(laite1, laite2, weight=float(viive_ms), loss=loss)
        self._paivita_pos_cache()

    def poista_yhteys(self, laite1, laite2):
        if not self.verkko.has_edge(laite1, laite2):
            raise ValueError(f"Yhteyttä {laite1} <--> {laite2} ei ole.")
        self.verkko.remove_edge(laite1, laite2)
        self._paivita_pos_cache()

    def muuta_yhteyden_viivetta(self, laite1, laite2, uusi_viive_ms):
        if not self.verkko.has_edge(laite1, laite2):
            raise ValueError(f"Yhteyttä {laite1} <--> {laite2} ei ole.")
        self.verkko[laite1][laite2]["weight"] = float(uusi_viive_ms)

    def muuta_yhteyden_havio(self, laite1, laite2, loss):
        if not self.verkko.has_edge(laite1, laite2):
            raise ValueError(f"Yhteyttä {laite1} <--> {laite2} ei ole.")
        loss = float(loss)
        if loss < 0.0 or loss > 1.0:
            raise ValueError("Häviön on oltava välillä 0.0 - 1.0.")
        self.verkko[laite1][laite2]["loss"] = loss

    # --- Simulaation asetukset ---

    def aseta_jitter(self, min_arvo, max_arvo):
        min_arvo = float(min_arvo)
        max_arvo = float(max_arvo)
        if min_arvo <= 0 or max_arvo <= 0 or min_arvo > max_arvo:
            raise ValueError("Jitter-arvojen tulee olla > 0 ja min <= max.")
        self.jitter_min = min_arvo
        self.jitter_max = max_arvo

    def aseta_nukkumisaika(self, sekunnit):
        sekunnit = float(sekunnit)
        if sekunnit < 0:
            raise ValueError("Nukkumisaika ei voi olla negatiivinen.")
        self.nukkumisaika = sekunnit

    # --- Tiedot ---

    def hae_laitteet(self):
        return list(self.verkko.nodes(data=True))

    def hae_yhteydet(self):
        return list(self.verkko.edges(data=True))

    def hae_pakettiloki(self):
        return list(self.pakettiloki)

    def hae_tilastot(self):
        maara = len(self.pakettiloki)
        if maara == 0:
            return {
                "maara": 0,
                "onnistuneet": 0,
                "epaonnistuneet": 0,
                "keskiviive": None,
                "min_viive": None,
                "max_viive": None,
            }
        onnistuneet = sum(1 for m in self.pakettiloki if m.get("onnistui", True))
        epaonnistuneet = maara - onnistuneet
        viiveet = [m["kokonaisviive_ms"] for m in self.pakettiloki]
        keskiviive = sum(viiveet) / len(viiveet)
        min_viive = min(viiveet)
        max_viive = max(viiveet)
        return {
            "maara": maara,
            "onnistuneet": onnistuneet,
            "epaonnistuneet": epaonnistuneet,
            "keskiviive": keskiviive,
            "min_viive": min_viive,
            "max_viive": max_viive,
        }

    # --- Simulaatio ---

    def laheta_viesti(self, lahettaja, vastaanottaja, viesti):
        if lahettaja not in self.verkko:
            raise ValueError(f"Lähettäjää '{lahettaja}' ei löydy.")
        if vastaanottaja not in self.verkko:
            raise ValueError(f"Vastaanottajaa '{vastaanottaja}' ei löydy.")

        try:
            reitti_suunniteltu = nx.shortest_path(
                self.verkko,
                source=lahettaja,
                target=vastaanottaja,
                weight="weight",
            )
        except nx.NetworkXNoPath:
            raise RuntimeError(f"Ei yhteyttä laitteiden {lahettaja} ja {vastaanottaja} välillä.")

        kokonaisviive = 0.0
        hopit = []
        kaytetty_reitti = [reitti_suunniteltu[0]]
        onnistui = True
        syy = ""

        for i in range(len(reitti_suunniteltu) - 1):
            nykyinen = reitti_suunniteltu[i]
            seuraava = reitti_suunniteltu[i + 1]
            edge_data = self.verkko[nykyinen][seuraava]
            viive = edge_data.get("weight", 0.0)
            loss_prob = edge_data.get("loss", 0.0)

            jitter = random.uniform(self.jitter_min, self.jitter_max)
            todellinen_viive = viive * jitter
            kokonaisviive += todellinen_viive

            lost = random.random() < loss_prob

            hopit.append(
                {
                    "lahto": nykyinen,
                    "kohde": seuraava,
                    "nimellinen_viive_ms": viive,
                    "jitter_kerroin": jitter,
                    "todellinen_viive_ms": todellinen_viive,
                    "loss_prob": loss_prob,
                    "lost": lost,
                }
            )

            if lost:
                onnistui = False
                syy = f"Paketti hävisi linkillä {nykyinen} -> {seuraava}"
                break

            kaytetty_reitti.append(seuraava)

            if self.nukkumisaika > 0:
                time.sleep(self.nukkumisaika)

        loki = {
            "aika": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lahettaja": lahettaja,
            "vastaanottaja": vastaanottaja,
            "viesti": viesti,
            "reitti_suunniteltu": reitti_suunniteltu,
            "reitti_toteutunut": kaytetty_reitti,
            "kokonaisviive_ms": kokonaisviive,
            "onnistui": onnistui,
            "syy": syy,
        }
        self.pakettiloki.append(loki)

        return {
            "reitti_suunniteltu": reitti_suunniteltu,
            "reitti_toteutunut": kaytetty_reitti,
            "kokonaisviive_ms": kokonaisviive,
            "hopit": hopit,
            "onnistui": onnistui,
            "syy": syy,
            "loki": loki,
        }

    # --- Esimerkkiverkko ---

    def luo_esimerkkiverkko(self):
        laitteet = [
            ("PC_Helsinki", "tietokone"),
            ("Reititin_A", "reititin"),
            ("Reititin_B", "reititin"),
            ("Reititin_C", "reititin"),
            ("Palvelin_Berlin", "tietokone"),
        ]
        for nimi, tyyppi in laitteet:
            if nimi not in self.verkko:
                self.lisaa_laite(nimi, tyyppi)

        yhteydet = [
            ("PC_Helsinki", "Reititin_A", 5, 0.0),
            ("Reititin_A", "Reititin_B", 50, 0.0),
            ("Reititin_A", "Reititin_C", 10, 0.0),
            ("Reititin_C", "Reititin_B", 10, 0.0),
            ("Reititin_B", "Palvelin_Berlin", 5, 0.0),
        ]
        for l1, l2, viive, loss in yhteydet:
            if not self.verkko.has_edge(l1, l2):
                self.lisaa_yhteys(l1, l2, viive_ms=viive, loss=loss)

    # --- Topologian tallennus ja lataus ---

    def export_topologia(self):
        nodes = []
        for n, data in self.verkko.nodes(data=True):
            nodes.append(
                {
                    "name": n,
                    "tyyppi": data.get("tyyppi", "reititin"),
                }
            )
        edges = []
        for u, v, data in self.verkko.edges(data=True):
            edges.append(
                {
                    "laite1": u,
                    "laite2": v,
                    "viive_ms": data.get("weight", 0.0),
                    "loss": data.get("loss", 0.0),
                }
            )
        topo = {
            "nodes": nodes,
            "edges": edges,
            "settings": {
                "jitter_min": self.jitter_min,
                "jitter_max": self.jitter_max,
                "nukkumisaika": self.nukkumisaika,
            },
        }
        return topo

    def import_topologia_dict(self, topo):
        self.verkko.clear()
        self._pos_cache = None

        for nd in topo.get("nodes", []):
            self.lisaa_laite(nd.get("name"), nd.get("tyyppi", "reititin"))

        for ed in topo.get("edges", []):
            l1 = ed.get("laite1")
            l2 = ed.get("laite2")
            viive = ed.get("viive_ms", 0.0)
            loss = ed.get("loss", 0.0)
            if l1 is None or l2 is None:
                continue
            if not self.verkko.has_edge(l1, l2):
                self.lisaa_yhteys(l1, l2, viive_ms=viive, loss=loss)

        settings = topo.get("settings", {})
        if settings:
            try:
                self.aseta_jitter(settings.get("jitter_min", self.jitter_min),
                                  settings.get("jitter_max", self.jitter_max))
                self.aseta_nukkumisaika(settings.get("nukkumisaika", self.nukkumisaika))
            except ValueError:
                # Jos tiedostossa on outoja arvoja, jätetään asetukset ennalleen
                pass


class VerkkoGUI(tk.Tk):
    """Tkinter-pohjainen graafinen käyttöliittymä verkkosimulaattorille."""

    def __init__(self):
        super().__init__()
        self.title("Verkkosimulaattori - GUI")
        self.geometry("1200x700")
        self.minsize(1000, 600)

        self.simu = Verkkosimulaattori()
        self.viimeisin_reitti = None
        self.viimeisin_onnistui = None

        self._luo_menu()
        self._luo_rakenne()
        self._luo_controlit()
        self._luo_visualisointi()

        self.paivita_verkko_tiedot()
        self.piirra_verkko()
        self.log("Tervetuloa Verkkosimulaattoriin! Lisää laitteita ja yhteyksiä vasemmalta.")

    # --- Rakenne ja valikko ---

    def _luo_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        tiedosto_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tiedosto", menu=tiedosto_menu)
        tiedosto_menu.add_command(label="Tallenna topologia...", command=self.tallenna_topologia_clicked)
        tiedosto_menu.add_command(label="Lataa topologia...", command=self.lataa_topologia_clicked)
        tiedosto_menu.add_separator()
        tiedosto_menu.add_command(label="Sulje", command=self.quit)

    def _luo_rakenne(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.control_frame = ttk.Frame(self, padding=5)
        self.control_frame.grid(row=0, column=0, sticky="nsew")

        self.right_frame = ttk.Frame(self, padding=5)
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        self.right_frame.rowconfigure(0, weight=1)
        self.right_frame.rowconfigure(1, weight=2)
        self.right_frame.columnconfigure(0, weight=1)

    def _luo_controlit(self):
        self.notebook = ttk.Notebook(self.control_frame)
        self.notebook.pack(fill="both", expand=True)

        # --- Laitteet-välilehti ---
        self.tab_laitteet = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_laitteet, text="Laitteet")

        ttk.Label(self.tab_laitteet, text="Laitteen nimi:").grid(row=0, column=0, sticky="w")
        self.entry_laite_nimi = ttk.Entry(self.tab_laitteet)
        self.entry_laite_nimi.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_laitteet, text="Tyyppi:").grid(row=1, column=0, sticky="w")
        self.cmb_laite_tyyppi = ttk.Combobox(
            self.tab_laitteet,
            values=["reititin", "tietokone"],
            state="readonly",
        )
        self.cmb_laite_tyyppi.set("reititin")
        self.cmb_laite_tyyppi.grid(row=1, column=1, sticky="ew", pady=2)

        btn_frame = ttk.Frame(self.tab_laitteet)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Lisää laite", command=self.lisaa_laite_clicked).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Päivitä tyyppi", command=self.paivita_laite_clicked).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Poista laite", command=self.poista_laite_clicked).pack(side="left", padx=2)

        ttk.Label(self.tab_laitteet, text="Laitteet:").grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.lb_laitteet = tk.Listbox(self.tab_laitteet, height=8)
        self.lb_laitteet.grid(row=4, column=0, columnspan=2, sticky="nsew")
        self.lb_laitteet.bind("<<ListboxSelect>>", self.laitelista_valittu)

        scroll_laitteet = ttk.Scrollbar(self.tab_laitteet, orient="vertical", command=self.lb_laitteet.yview)
        scroll_laitteet.grid(row=4, column=2, sticky="ns")
        self.lb_laitteet.configure(yscrollcommand=scroll_laitteet.set)

        self.tab_laitteet.columnconfigure(1, weight=1)
        self.tab_laitteet.rowconfigure(4, weight=1)

        # --- Yhteydet-välilehti ---
        self.tab_yhteydet = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_yhteydet, text="Yhteydet")

        ttk.Label(self.tab_yhteydet, text="Laite 1:").grid(row=0, column=0, sticky="w")
        self.cb_y_l1 = ttk.Combobox(self.tab_yhteydet, state="readonly")
        self.cb_y_l1.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_yhteydet, text="Laite 2:").grid(row=1, column=0, sticky="w")
        self.cb_y_l2 = ttk.Combobox(self.tab_yhteydet, state="readonly")
        self.cb_y_l2.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_yhteydet, text="Viive (ms):").grid(row=2, column=0, sticky="w")
        self.entry_y_viive = ttk.Entry(self.tab_yhteydet)
        self.entry_y_viive.grid(row=2, column=1, sticky="ew", pady=2)
        self.entry_y_viive.insert(0, "10")

        ttk.Label(self.tab_yhteydet, text="Häviö (%):").grid(row=3, column=0, sticky="w")
        self.entry_y_loss = ttk.Entry(self.tab_yhteydet)
        self.entry_y_loss.grid(row=3, column=1, sticky="ew", pady=2)
        self.entry_y_loss.insert(0, "0")

        btn_frame_y = ttk.Frame(self.tab_yhteydet)
        btn_frame_y.grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")
        ttk.Button(btn_frame_y, text="Lisää yhteys", command=self.lisaa_yhteys_clicked).pack(side="left", padx=2)
        ttk.Button(btn_frame_y, text="Muuta viivettä/häviötä", command=self.muuta_yhteys_clicked).pack(side="left", padx=2)
        ttk.Button(btn_frame_y, text="Poista yhteys", command=self.poista_yhteys_clicked).pack(side="left", padx=2)

        ttk.Label(self.tab_yhteydet, text="Yhteydet:").grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.lb_yhteydet = tk.Listbox(self.tab_yhteydet, height=8)
        self.lb_yhteydet.grid(row=6, column=0, columnspan=2, sticky="nsew")
        self.lb_yhteydet.bind("<<ListboxSelect>>", self.yhteyslista_valittu)

        scroll_yhteydet = ttk.Scrollbar(self.tab_yhteydet, orient="vertical", command=self.lb_yhteydet.yview)
        scroll_yhteydet.grid(row=6, column=2, sticky="ns")
        self.lb_yhteydet.configure(yscrollcommand=scroll_yhteydet.set)

        self.tab_yhteydet.columnconfigure(1, weight=1)
        self.tab_yhteydet.rowconfigure(6, weight=1)

        # --- Simulaatio-välilehti ---
        self.tab_simulaatio = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_simulaatio, text="Simulaatio")

        ttk.Label(self.tab_simulaatio, text="Lähettävä laite:").grid(row=0, column=0, sticky="w")
        self.cb_s_lahettaja = ttk.Combobox(self.tab_simulaatio, state="readonly")
        self.cb_s_lahettaja.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_simulaatio, text="Vastaanottava laite:").grid(row=1, column=0, sticky="w")
        self.cb_s_vastaanottaja = ttk.Combobox(self.tab_simulaatio, state="readonly")
        self.cb_s_vastaanottaja.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_simulaatio, text="Viesti:").grid(row=2, column=0, sticky="w")
        self.entry_s_viesti = ttk.Entry(self.tab_simulaatio)
        self.entry_s_viesti.grid(row=2, column=1, sticky="ew", pady=2)

        btn_frame_s = ttk.Frame(self.tab_simulaatio)
        btn_frame_s.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        ttk.Button(btn_frame_s, text="Lähetä viesti", command=self.laheta_viesti_clicked).pack(side="left", padx=2)
        ttk.Button(btn_frame_s, text="Näytä pakettiloki", command=self.nayta_pakettiloki_clicked).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame_s, text="Näytä tilastot", command=self.nayta_tilastot_clicked).pack(
            side="left", padx=2
        )

        self.tab_simulaatio.columnconfigure(1, weight=1)

        # --- Asetukset-välilehti ---
        self.tab_asetukset = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.tab_asetukset, text="Asetukset")

        ttk.Label(self.tab_asetukset, text="Jitter min:").grid(row=0, column=0, sticky="w")
        self.entry_jitter_min = ttk.Entry(self.tab_asetukset)
        self.entry_jitter_min.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_asetukset, text="Jitter max:").grid(row=1, column=0, sticky="w")
        self.entry_jitter_max = ttk.Entry(self.tab_asetukset)
        self.entry_jitter_max.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(self.tab_asetukset, text="Nukkumisaika (s/linkki):").grid(row=2, column=0, sticky="w")
        self.entry_nukkumisaika = ttk.Entry(self.tab_asetukset)
        self.entry_nukkumisaika.grid(row=2, column=1, sticky="ew", pady=2)

        btn_frame_a = ttk.Frame(self.tab_asetukset)
        btn_frame_a.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        ttk.Button(btn_frame_a, text="Tallenna asetukset", command=self.tallenna_asetukset_clicked).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame_a, text="Luo esimerkkiverkko", command=self.luo_esimerkkiverkko_clicked).pack(
            side="left", padx=2
        )

        # Aseta oletusarvot kenttiin
        self.entry_jitter_min.insert(0, str(self.simu.jitter_min))
        self.entry_jitter_max.insert(0, str(self.simu.jitter_max))
        self.entry_nukkumisaika.insert(0, str(self.simu.nukkumisaika))

        self.tab_asetukset.columnconfigure(1, weight=1)

    def _luo_visualisointi(self):
        # Lokiruutu
        log_frame = ttk.LabelFrame(self.right_frame, text="Tapahtumaloki")
        log_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap="word", height=10, state="normal")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll_log = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll_log.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll_log.set)

        btn_frame_log = ttk.Frame(log_frame)
        btn_frame_log.grid(row=1, column=0, columnspan=2, sticky="e", pady=(2, 0))
        ttk.Button(btn_frame_log, text="Tyhjennä näkymä", command=self.tyhjenna_loki_nakyma).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame_log, text="Tyhjennä pakettiloki", command=self.tyhjenna_pakettiloki).pack(
            side="left", padx=2
        )

        # Verkon visualisointi
        graph_frame = ttk.LabelFrame(self.right_frame, text="Verkon topologia")
        graph_frame.grid(row=1, column=0, sticky="nsew")
        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=1)

        self.figure = plt.Figure(figsize=(6, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

    # --- Apufunktiot GUI:lle ---

    def log(self, msg: str):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        print(msg)

    def tyhjenna_loki_nakyma(self):
        self.log_text.delete("1.0", "end")

    def tyhjenna_pakettiloki(self):
        self.simu.pakettiloki.clear()
        self.log("Pakettiloki tyhjennetty.")

    def paivita_verkko_tiedot(self):
        laitteet = self.simu.hae_laitteet()
        self.lb_laitteet.delete(0, tk.END)
        node_names = []
        for nimi, data in laitteet:
            tyyppi = data.get("tyyppi", "?")
            self.lb_laitteet.insert(tk.END, f"{nimi} ({tyyppi})")
            node_names.append(nimi)

        for cb in [self.cb_y_l1, self.cb_y_l2, self.cb_s_lahettaja, self.cb_s_vastaanottaja]:
            cb["values"] = node_names

        yhteydet = self.simu.hae_yhteydet()
        self.lb_yhteydet.delete(0, tk.END)
        for laite1, laite2, data in yhteydet:
            viive = data.get("weight", 0.0)
            loss = data.get("loss", 0.0) * 100.0
            self.lb_yhteydet.insert(
                tk.END,
                f"{laite1} <--> {laite2} (viive: {viive:.1f} ms, häviö: {loss:.1f} %)",
            )

    def piirra_verkko(self):
        self.ax.clear()
        if self.simu._pos_cache is None:
            self.simu._paivita_pos_cache()
        pos = self.simu._pos_cache

        if self.simu.verkko.number_of_nodes() > 0:
            nodes = list(self.simu.verkko.nodes)
            base_colors = [self.simu.verkko.nodes[n].get("color", "lightblue") for n in nodes]

            # korosta viimeisin reitti suuremmilla solmuilla
            node_sizes = []
            route_set = set(self.viimeisin_reitti) if self.viimeisin_reitti else set()
            for n in nodes:
                if n in route_set:
                    node_sizes.append(1700)
                else:
                    node_sizes.append(1200)

            edges = list(self.simu.verkko.edges())
            edge_colors = []
            edge_widths = []
            reitti_edge_set = set()
            if self.viimeisin_reitti and len(self.viimeisin_reitti) > 1:
                for i in range(len(self.viimeisin_reitti) - 1):
                    a = self.viimeisin_reitti[i]
                    b = self.viimeisin_reitti[i + 1]
                    reitti_edge_set.add((a, b))
                    reitti_edge_set.add((b, a))

            for (u, v) in edges:
                if (u, v) in reitti_edge_set or (v, u) in reitti_edge_set:
                    edge_colors.append("red")
                    edge_widths.append(3.0)
                else:
                    edge_colors.append("gray")
                    edge_widths.append(1.0)

            nx.draw(
                self.simu.verkko,
                pos,
                ax=self.ax,
                with_labels=True,
                node_color=base_colors,
                node_size=node_sizes,
                font_weight="bold",
                edge_color=edge_colors,
                width=edge_widths,
            )
            labels = nx.get_edge_attributes(self.simu.verkko, "weight")
            if labels:
                nx.draw_networkx_edge_labels(
                    self.simu.verkko,
                    pos,
                    edge_labels=labels,
                    ax=self.ax,
                )

        title = "Verkon topologia"
        if self.viimeisin_reitti:
            if self.viimeisin_onnistui:
                title += " (viimeisin reitti korostettu)"
            else:
                title += " (viimeisin reitti epäonnistui)"
        self.ax.set_title(title)
        self.ax.axis("off")
        self.figure.tight_layout()
        self.canvas.draw()

    # --- Tapahtumankäsittelijät ---

    def laitelista_valittu(self, event):
        sel = self.lb_laitteet.curselection()
        if not sel:
            return
        teksti = self.lb_laitteet.get(sel[0])
        if " (" in teksti:
            nimi = teksti.split(" (", 1)[0]
        else:
            nimi = teksti
        self.entry_laite_nimi.delete(0, tk.END)
        self.entry_laite_nimi.insert(0, nimi)

        data = self.simu.verkko.nodes.get(nimi, {})
        tyyppi = data.get("tyyppi", "reititin")
        if tyyppi in ["reititin", "tietokone"]:
            self.cmb_laite_tyyppi.set(tyyppi)

    def yhteyslista_valittu(self, event):
        sel = self.lb_yhteydet.curselection()
        if not sel:
            return
        line = self.lb_yhteydet.get(sel[0])
        # odotettu muoto:
        # "A <--> B (viive: X ms, häviö: Y %)"
        try:
            osat = line.split(" <--> ")
            l1 = osat[0].strip()
            loppu = osat[1]
            l2 = loppu.split(" (", 1)[0].strip()
        except Exception:
            return
        self.cb_y_l1.set(l1)
        self.cb_y_l2.set(l2)

        try:
            if "viive:" in line:
                viive_str = line.split("viive:")[1].split("ms")[0].strip()
                self.entry_y_viive.delete(0, tk.END)
                self.entry_y_viive.insert(0, viive_str)
        except Exception:
            pass

        try:
            if "häviö:" in line:
                loss_str = line.split("häviö:")[1].split("%")[0].strip()
                self.entry_y_loss.delete(0, tk.END)
                self.entry_y_loss.insert(0, loss_str)
        except Exception:
            pass

    def lisaa_laite_clicked(self):
        nimi = self.entry_laite_nimi.get().strip()
        tyyppi = self.cmb_laite_tyyppi.get().strip() or "reititin"
        try:
            self.simu.lisaa_laite(nimi, tyyppi)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(f"Laite lisätty: {nimi} ({tyyppi})")
        self.paivita_verkko_tiedot()
        self.piirra_verkko()

    def paivita_laite_clicked(self):
        nimi = self.entry_laite_nimi.get().strip()
        tyyppi = self.cmb_laite_tyyppi.get().strip() or "reititin"
        try:
            self.simu.muokkaa_laitetta(nimi, tyyppi)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(f"Laitteen '{nimi}' tyyppi päivitetty: {tyyppi}")
        self.paivita_verkko_tiedot()
        self.piirra_verkko()

    def poista_laite_clicked(self):
        nimi = self.entry_laite_nimi.get().strip()
        if not nimi:
            sel = self.lb_laitteet.curselection()
            if sel:
                teksti = self.lb_laitteet.get(sel[0])
                if " (" in teksti:
                    nimi = teksti.split(" (", 1)[0]
        if not nimi:
            messagebox.showerror("Virhe", "Valitse tai kirjoita poistettava laite.", parent=self)
            return
        try:
            self.simu.poista_laite(nimi)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(f"Laite poistettu: {nimi}")
        self.entry_laite_nimi.delete(0, tk.END)
        self.paivita_verkko_tiedot()
        self.piirra_verkko()

    def lisaa_yhteys_clicked(self):
        l1 = self.cb_y_l1.get().strip()
        l2 = self.cb_y_l2.get().strip()
        viive_str = self.entry_y_viive.get().strip() or "10"
        loss_str = self.entry_y_loss.get().strip() or "0"
        try:
            viive = float(viive_str)
        except ValueError:
            messagebox.showerror("Virhe", "Viiveen tulee olla numero.", parent=self)
            return
        try:
            loss_percent = float(loss_str)
        except ValueError:
            messagebox.showerror("Virhe", "Häviön tulee olla numero.", parent=self)
            return
        loss_prob = max(0.0, min(1.0, loss_percent / 100.0))
        try:
            self.simu.lisaa_yhteys(l1, l2, viive_ms=viive, loss=loss_prob)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(f"Yhteys lisätty: {l1} <--> {l2} (viive {viive:.1f} ms, häviö {loss_prob*100:.1f} %)")
        self.paivita_verkko_tiedot()
        self.piirra_verkko()

    def muuta_yhteys_clicked(self):
        l1 = self.cb_y_l1.get().strip()
        l2 = self.cb_y_l2.get().strip()
        viive_str = self.entry_y_viive.get().strip()
        loss_str = self.entry_y_loss.get().strip()
        if not viive_str:
            messagebox.showerror("Virhe", "Anna uusi viive.", parent=self)
            return
        try:
            viive = float(viive_str)
        except ValueError:
            messagebox.showerror("Virhe", "Viiveen tulee olla numero.", parent=self)
            return
        try:
            loss_percent = float(loss_str)
        except ValueError:
            messagebox.showerror("Virhe", "Häviön tulee olla numero.", parent=self)
            return
        loss_prob = max(0.0, min(1.0, loss_percent / 100.0))
        try:
            self.simu.muuta_yhteyden_viivetta(l1, l2, viive)
            self.simu.muuta_yhteyden_havio(l1, l2, loss_prob)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(f"Yhteyden {l1} <--> {l2} viive/häviö päivitetty: {viive:.1f} ms, häviö {loss_prob*100:.1f} %")
        self.paivita_verkko_tiedot()
        self.piirra_verkko()

    def poista_yhteys_clicked(self):
        l1 = self.cb_y_l1.get().strip()
        l2 = self.cb_y_l2.get().strip()
        try:
            self.simu.poista_yhteys(l1, l2)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(f"Yhteys poistettu: {l1} <--> {l2}")
        self.paivita_verkko_tiedot()
        self.piirra_verkko()

    def laheta_viesti_clicked(self):
        lahettaja = self.cb_s_lahettaja.get().strip()
        vastaanottaja = self.cb_s_vastaanottaja.get().strip()
        viesti = self.entry_s_viesti.get().strip() or "(tyhjä viesti)"
        try:
            tulos = self.simu.laheta_viesti(lahettaja, vastaanottaja, viesti)
        except (ValueError, RuntimeError) as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return

        self.viimeisin_reitti = tulos["reitti_toteutunut"]
        self.viimeisin_onnistui = tulos["onnistui"]
        self.piirra_verkko()

        self.log(f"--- Lähetys {lahettaja} -> {vastaanottaja} ---")
        self.log("Suunniteltu reitti: " + " -> ".join(tulos["reitti_suunniteltu"]))
        self.log("Toteutunut reitti: " + " -> ".join(tulos["reitti_toteutunut"]))
        for hop in tulos["hopit"]:
            rivi = (
                f"  {hop['lahto']} -> {hop['kohde']} | nimellinen {hop['nimellinen_viive_ms']} ms, "
                f"todellinen {hop['todellinen_viive_ms']:.1f} ms (jitter {hop['jitter_kerroin']:.2f}x)"
            )
            if hop.get("loss_prob", 0.0) > 0.0:
                rivi += f" | häviö {hop['loss_prob']*100:.1f} %"
            if hop.get("lost"):
                rivi += "  <-- PAKETTI HÄVISI TÄHÄN"
            self.log(rivi)
        if tulos["onnistui"]:
            self.log(f"Kokonaisviive: {tulos['kokonaisviive_ms']:.1f} ms")
            self.log("Paketti saapui perille.")
        else:
            self.log(f"Paketti EI saapunut perille: {tulos['syy']}")
            self.log(f"Kokonaisviive ennen häviötä: {tulos['kokonaisviive_ms']:.1f} ms")
        self.log(f"Viestin sisältö: {viesti}")
        self.log("")

    def nayta_pakettiloki_clicked(self):
        loki = self.simu.hae_pakettiloki()
        if not loki:
            self.log("Pakettiloki on tyhjä.")
            return
        self.log("--- Pakettiloki ---")
        for merkinta in loki:
            status = "OK" if merkinta.get("onnistui", True) else "EPÄONNISTUI"
            self.log(
                f"[{merkinta['aika']}] {merkinta['lahettaja']} -> {merkinta['vastaanottaja']} | "
                f"{status} | viive {merkinta['kokonaisviive_ms']:.1f} ms | "
                f"reitti: {' -> '.join(merkinta['reitti_toteutunut'])}"
            )
        self.log("--- Pakettiloki loppu ---")
        self.log("")

    def nayta_tilastot_clicked(self):
        til = self.simu.hae_tilastot()
        if til["maara"] == 0:
            self.log("Ei vielä lähetettyjä paketteja, ei tilastoja.")
            return
        self.log("--- Tilastot ---")
        self.log(f"Lähetettyjä paketteja: {til['maara']}")
        self.log(f"Onnistuneet: {til['onnistuneet']}")
        self.log(f"Epäonnistuneet: {til['epaonnistuneet']}")
        self.log(f"Keskimääräinen viive: {til['keskiviive']:.1f} ms")
        self.log(f"Pienin viive: {til['min_viive']:.1f} ms")
        self.log(f"Suurin viive: {til['max_viive']:.1f} ms")
        self.log("--- Tilastot loppu ---")
        self.log("")

    def tallenna_asetukset_clicked(self):
        jitter_min = self.entry_jitter_min.get().strip()
        jitter_max = self.entry_jitter_max.get().strip()
        nukkumisaika = self.entry_nukkumisaika.get().strip()
        try:
            self.simu.aseta_jitter(jitter_min, jitter_max)
            self.simu.aseta_nukkumisaika(nukkumisaika)
        except ValueError as e:
            messagebox.showerror("Virhe", str(e), parent=self)
            return
        self.log(
            f"Asetukset päivitetty: jitter {self.simu.jitter_min:.2f} - {self.simu.jitter_max:.2f}, "
            f"nukkumisaika {self.simu.nukkumisaika:.2f} s/linkki"
        )

    def luo_esimerkkiverkko_clicked(self):
        self.simu.luo_esimerkkiverkko()
        self.paivita_verkko_tiedot()
        self.piirra_verkko()
        self.log("Esimerkkiverkko lisätty (Helsinki -> Berlin).")

    def tallenna_topologia_clicked(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Tallenna topologia",
            defaultextension=".json",
            filetypes=[("JSON-tiedostot", "*.json"), ("Kaikki tiedostot", "*.*")],
        )
        if not path:
            return
        topo = self.simu.export_topologia()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(topo, f, ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror("Virhe", f"Tallennus epäonnistui: {e}", parent=self)
            return
        self.log(f"Topologia tallennettu: {path}")

    def lataa_topologia_clicked(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Lataa topologia",
            filetypes=[("JSON-tiedostot", "*.json"), ("Kaikki tiedostot", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                topo = json.load(f)
            self.simu.import_topologia_dict(topo)
        except (OSError, json.JSONDecodeError) as e:
            messagebox.showerror("Virhe", f"Lataus epäonnistui: {e}", parent=self)
            return
        self.entry_jitter_min.delete(0, tk.END)
        self.entry_jitter_min.insert(0, str(self.simu.jitter_min))
        self.entry_jitter_max.delete(0, tk.END)
        self.entry_jitter_max.insert(0, str(self.simu.jitter_max))
        self.entry_nukkumisaika.delete(0, tk.END)
        self.entry_nukkumisaika.insert(0, str(self.simu.nukkumisaika))
        self.viimeisin_reitti = None
        self.viimeisin_onnistui = None
        self.paivita_verkko_tiedot()
        self.piirra_verkko()
        self.log(f"Topologia ladattu: {path}")


if __name__ == "__main__":
    app = VerkkoGUI()
    app.mainloop()
