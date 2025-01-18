import io
import textwrap
import streamlit as st
import pandas as pd
import zipfile
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, shapiro, spearmanr
from docx import Document
from streamlit import session_state
from packages.functions import khi2, anova, repeated_anova, correlation, add_df_to_doc

#Configuration de la page
st.set_page_config(layout="wide",
                   page_icon="📉",
                   page_title="xatix"
                   )

#Liste des analyses
list_analysis = {
    "Regression":["Linéaire", "Logistique", "Quantile"],
    "Association":["Khi 2", "Gamma"],
    "Correlation":["Pearson", "Spearman"],
    "Comparaison moyennes":None,
    "Comparaison inter/intra groupes":None
}


#Jeu de données initial :
#TODO: Coder l'importation et la sauvegarde des jeux de données


#Utilisateur
user = "user1"


# Page d'accueil
st.title("Plateforme d'analyses des données")
st.sidebar.title("Menu")


menu = st.sidebar.radio(
    "Choisissez une option",
    ["Accueil",
     "Regression",
     "Association",
     "Correlation",
     "Comparaison moyennes",
     "Comparaison inter/intra groupes",
    "Aide"]
)


if "data" not in session_state:
    st.session_state["data"] = pd.DataFrame()

if menu in ("Regression","Association","Correlation",
            "Comparaison moyennes","Comparaison inter/intra groupes"):
    st.header("Data set")  # Titre de la section dédiée à l'affichage du jeu de données


    uploaded_file = st.file_uploader("Importer un jeu de données", type=["xlsx","xls", "csv"])
    if uploaded_file != None :
        data = uploaded_file.getvalue()
        try:
            st.session_state["data"] = pd.read_excel(data)

        except TypeError:
            st.session_state["data"] = pd.read_csv(data)

        except NameError:
            st.session_state["data"] = pd.DataFrame()
            st.write("Bien vouloir téléverser un jeu de données")

    st.dataframe(st.session_state["data"], use_container_width=True, hide_index=True)  # Affichage du jeu de données

    if not st.session_state["data"].empty:
        list_vars = st.session_state["data"].columns  # Liste des variables contenues dans le jeu de données
        num_vars = [var for var in list_vars if st.session_state["data"][var].dtype != "O"]  # Variables quantitatives
        cat_vars = [var for var in list_vars if st.session_state["data"][var].dtype == "O"]  # Variables qualitatives

    else :
        num_vars,cat_vars = list(),list()

    st.divider()  # Ligne horizontale


# ==================== Comparaison inter et intra groupes ====================
if menu == "Comparaison inter/intra groupes":

    st.header("Comparaisons entre groupes à des moments différents")


    st.header("Analyses")  # Titre de la section dédiée au choix des variables de l'analyse

    st.divider()  # Ligne horizontale
    # 4 colonnes qui doivent contenir les selectbox pour el choix des types d'analyse et des variables
    col1, col2, col3 = st.columns(3)
    analyses = Document()

    with col1:

        def initialize_buffer_doc():
            # Création d'un document mois en mémoire dans session_state
            analyses = Document()

        # Selectbox to choose the group var
        select_group = st.selectbox(
            "Variable de groupes:",
            cat_vars,
            on_change=initialize_buffer_doc,
            key="_group"
        )

    with col2:
        # Selectbox to choose the group var
        select_time = st.selectbox(
            "Variable de temps:",
            [var for var in cat_vars if var !=select_group],
            on_change=initialize_buffer_doc,
            key="_time"
        )

    with col3:
        select_dependent = st.multiselect(
            "Variable(s) dépendantes:",
            num_vars,
            on_change=initialize_buffer_doc,
            key="_dependent"
        )

    st.divider()

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results"]})

    col4, col5 = st.columns(2)

    condition = (select_group==None) or (select_time==None) or len(select_dependent)==0

    with col4:
        st.subheader("Résultats")
        st.divider()

        if not condition:

            # Comparaisons inter-groupes
            st.markdown("* ***Comparaisons inter-groupes***")

            for time in st.session_state["data"][select_time].unique():
                st.subheader("En {} ".format(time))
                analyses.add_paragraph("En {} ".format(time))
                data_time = st.session_state["data"][st.session_state["data"][select_time] == time]
                for val in select_dependent:
                    st.write(val)

                    sortie = anova(data_time, select_group, val, analyses)

                    st.write("Test de normalité ({}) et d'homocédasticité (Bartlett) : ".format(sortie[3]))
                    st.dataframe(sortie[0], use_container_width=True, hide_index=True)
                    st.write("Test de comparaison ({}) : ".format(sortie[4]))
                    st.dataframe(sortie[1], use_container_width=True, hide_index=True)
                    if sortie[4] in ["kruskal", "anova"]:
                        st.write("Analyse post hoc")
                        try:
                            st.dataframe(sortie[6], use_container_width=True)
                        except:
                            st.write("Pas d'analyse post hoc")

            analyses = sortie[5]

            # Comparaisons intra-groupes
            st.markdown("* ***Comparaisons intra-groupes***")

            for gr in st.session_state["data"][select_group].unique():
                st.subheader("Groupe {} ".format(gr))
                analyses.add_paragraph("Groupe {} ".format(gr))
                data_gr = st.session_state["data"][st.session_state["data"][select_group] == gr]
                for val in select_dependent:
                    st.write(val)

                    sortie = repeated_anova(data_gr, select_time, val, analyses)

                    st.write("Test de normalité ({}) et d'homocédasticité (Bartlett) : ".format(sortie[3]))
                    st.dataframe(sortie[0], use_container_width=True, hide_index=True)
                    st.write("Test de comparaison ({}) : ".format(sortie[4]))
                    st.dataframe(sortie[1], use_container_width=True, hide_index=True)
                    if sortie[4] in ["friedman", "anova"]:
                        st.write("Analyse post hoc")
                        st.dataframe(sortie[6], use_container_width=True)

            analyses = sortie[5]
            bio = io.BytesIO()
            analyses.save(bio)
            resultats_analyses = bio.getvalue()
            graphiques = dict()

    with col5:
        st.subheader("Graphiques")
        st.divider()

        if not condition:

            for time in st.session_state["data"][select_time].unique():
                data_time = st.session_state["data"][st.session_state["data"][select_time] == time]

                l = list(st.session_state["data"][select_group].unique())
                l.sort()
                for val in select_dependent:
                    arrays = [list(data_time[data_time[select_group] == groupe][val]) for groupe in l]
                    fig, ax = plt.subplots()
                    bp = plt.boxplot(arrays, labels=l, showmeans=True, patch_artist=True)
                    plt.title("En {} : {}".format(time, val))

                    bio = io.BytesIO()
                    plt.savefig(bio, dpi=250, format="png")
                    graphiques["{}_{}".format(time, val)] = bio.getvalue()


                    for box in bp["boxes"]:
                        box.set_facecolor('lightblue')

                    st.pyplot(fig)

                    # Cleanup plot
                    plt.close(plt.gcf())
                    plt.clf()

            for gr in st.session_state["data"][select_group].unique():
                data_gr = st.session_state["data"][st.session_state["data"][select_group] == gr]

                # TODO: adding the below plots to the document session.state[analyses]
                l = list(st.session_state["data"][select_time].unique())
                l.sort()
                for val in select_dependent:
                    arrays = [list(data_gr[data_gr[select_time] == groupe][val]) for groupe in l]
                    fig, ax = plt.subplots()
                    bp = plt.boxplot(arrays, labels=l, showmeans=True, patch_artist=True)
                    plt.title("Groupe {} : {}".format(gr, val))

                    bio = io.BytesIO()
                    plt.savefig(bio, dpi=250, format="png")
                    graphiques["{}_{}".format(gr, val)] = bio.getvalue()

                    for box in bp["boxes"]:
                        box.set_facecolor('lightblue')

                    st.pyplot(fig)

                    # Cleanup plot
                    plt.close(plt.gcf())
                    plt.clf()

    #Bouton d'enregistrement des analyses
    if not condition:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "x") as zip:
            zip.writestr("rapport.docx", resultats_analyses)
            for key in graphiques:
                zip.writestr(key+".png",graphiques[key])

    if not condition:

        st.sidebar.divider()
        st.sidebar.write("Télécharger les résultats des analyses")
        st.sidebar.download_button(
            label="Télécharger au format Word :arrow_down:",
            data=buf.getvalue(),
            file_name="resultats.zip",
            mime="application/zip",
            type="primary",
            disabled=(sortie == None)
        )
    else:
        st.sidebar.divider()
        st.sidebar.button(
            label="Télécharger",
            disabled=True
        )

# ==================== Comparaison des moyennes ====================
elif menu == "Comparaison moyennes":
    st.header("Comparaisons des groupes")


    st.header("Analyses")  # Titre de la section dédiée au choix des variables de l'analyse

    # 4 colonnes qui doivent contenir les selectbox pour el choix des types d'analyse et des variables
    col1, col2 = st.columns(2)
    st.divider()  # Ligne horizontale
    analyses = Document()

    with col1:

        def initialize_buffer_doc():
            # Création d'un document mois en mémoire dans session_state
            analyses = Document()

        # Selectbox to choose the group var
        select_group = st.selectbox(
            "Variable de temps:",
            [var for var in cat_vars],
            on_change=initialize_buffer_doc,
            key="_time"
        )

    with col2:

        select_dependent = st.multiselect(
            "Variable(s) dépendantes:",
            num_vars,
            on_change=initialize_buffer_doc,
            key="_dependent"
        )

    st.divider()

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results"]})

    col4, col5 = st.columns(2)

    condition = (select_group == None) or len(select_dependent) == 0

    with col4:
        st.subheader("Résultats")
        st.divider()

        if not condition:
            # Comparaisons des groupes
            for val in select_dependent:
                st.write(val)

                try:

                    sortie = anova(st.session_state["data"], select_group, val, analyses)

                    st.write("Test de normalité ({}) et d'homocédasticité (Bartlett) : ".format(sortie[3]))
                    st.dataframe(sortie[0], use_container_width=True, hide_index=True)
                    st.write("Test de comparaison ({}) : ".format(sortie[4]))
                    st.dataframe(sortie[1], use_container_width=True, hide_index=True)
                    if sortie[4] in ["kruskal", "anova"]:
                        st.write("Analyse post hoc")
                        try:
                            st.dataframe(sortie[6], use_container_width=True)
                        except:
                            st.write("Pas d'analyse post hoc")
                    analyses = sortie[5]

                except:
                    st.write("Une erreur est survenue !")

    with col5:
        bio = io.BytesIO()
        analyses.save(bio)
        resultats_analyses = bio.getvalue()
        graphiques = dict()
        st.subheader("Graphiques")
        st.divider()

        if not condition:
            l = list(st.session_state["data"][select_group].unique())
            l.sort()
            for val in select_dependent:
                arrays = [list(st.session_state["data"][st.session_state["data"][select_group] == groupe][val]) for groupe in l]
                fig, ax = plt.subplots()
                bp = plt.boxplot(arrays, labels=l, showmeans=True, patch_artist=True)
                plt.title("{}".format(val))

                bio = io.BytesIO()
                plt.savefig(bio, dpi=250, format="png")
                graphiques["{}".format(val)] = bio.getvalue()

                for box in bp["boxes"]:
                    box.set_facecolor('lightblue')

                st.pyplot(fig)

                # Cleanup plot
                plt.close(plt.gcf())
                plt.clf()

    # Bouton d'enregistrement des analyses
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "x") as zip:
        zip.writestr("rapport.docx", resultats_analyses)
        for key in graphiques:
            zip.writestr(key + ".png", graphiques[key])

    try:
        st.sidebar.divider()
        st.sidebar.write("Télécharger les résultats des analyses")
        st.sidebar.download_button(
            label="Télécharger au format Word :arrow_down:",
            data=buf.getvalue(),
            file_name="resultats.zip",
            mime="application/zip",
            type="primary",
            disabled=(sortie == None)
        )
    except:
        st.sidebar.divider()
        st.sidebar.button(
            label="Télécharger",
            disabled=True
        )

# ==================== Corrélations ====================
elif menu == "Correlation":
    st.header("Corrélations entre variables quantitatives")

    st.divider()  # Ligne horizontale
    analyses = Document()

    def initialize_buffer_doc():
        # Création d'un document mois en mémoire dans session_state
        analyses = Document()

    select_vars = st.multiselect(
        "Variable(s) :",
        num_vars,
        on_change=initialize_buffer_doc,
        key="_vars"
    )

    st.divider()
    st.subheader("Résultats")

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results"]})

    col2, col3 = st.columns(2)

    condition = len(select_vars) < 2

    if condition:
        st.write("Bien vouloir sélectionner au moins deux variables quantitatives")
    else:
        corr_pear = correlation(st.session_state["data"][select_vars], "pearson", "Correlation map : Pearson")
        # Spearman
        corr_sp = correlation(st.session_state["data"][select_vars], "spearman", "Correlation map : Spearman")

        with col2:
            st.divider()
            # Pearson
            st.subheader("Test de Shapiro-Wilk (normalité) : p-value")
            st.dataframe(corr_pear[0],hide_index=True)

            st.subheader("Coefficient de corrélation de Pearson")
            st.dataframe(corr_pear[1])

            st.subheader("Coefficient de corrélation de Spearman")
            st.dataframe(corr_sp[1])

            add_df_to_doc(corr_pear[0], analyses, "Normalité")
            add_df_to_doc(corr_pear[1], analyses, "Corrélation de Pearson")
            add_df_to_doc(corr_sp[1],analyses,"Corrélation de Spearman")


        with col3:
            st.divider()

            st.subheader("Représentation graphique des corrélations ")
            # Drawing the plot in the web page
            st.pyplot(corr_pear[2])
            # hand buffer to python-docx
            analyses.add_picture(corr_pear[3])

            # Cleanup plot
            plt.close(plt.gcf())
            plt.clf()

            #Drawing the plot in the web page
            st.pyplot(corr_sp[2])
            # hand buffer to python-docx
            analyses.add_picture(corr_sp[3])

            # Cleanup plot
            plt.close(plt.gcf())
            plt.clf()

    # Bouton d'enregistrement des analyses
    buffer = io.BytesIO()
    bio = io.BytesIO()
    analyses.save(bio)
    resultats_analyses = bio.getvalue()
    with zipfile.ZipFile(buffer, "x") as zip:
        zip.writestr("correlations.docx", resultats_analyses)


    try:
        st.sidebar.divider()
        st.sidebar.write("Télécharger les résultats des analyses")
        st.sidebar.download_button(
            label="Télécharger au format Word :arrow_down:",
            data=buffer.getvalue(),
            file_name="resultats.zip",
            mime="application/zip",
            type="primary",
            disabled=condition
        )
    except:
        st.sidebar.divider()
        st.sidebar.button(
            label="Télécharger",
            disabled=True
        )

# ==================== Associations ====================
elif menu == "Association":
    st.header("Association entre variables qualitatives")

    st.divider()  # Ligne horizontale
    analyses = Document()

    def initialize_buffer_doc():
        # Création d'un document mois en mémoire dans session_state
        analyses = Document()

    col1,col2 = st.columns(2)

    with col1:
        select_var_ligne = st.multiselect(
            "Variable(s) ligne(s) :",
            cat_vars,
            on_change=initialize_buffer_doc,
            key="_var_ligne"
        )

    with col2:
        select_var_colonne = st.multiselect(
            "Variable(s) colonne(s) :",
            [var for var in cat_vars if var not in select_var_ligne],
            on_change=initialize_buffer_doc,
            key="_var_colonne"
        )



    st.subheader("Résultats")

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results"]})

    col3, col4 = st.columns(2)

    condition = (len(select_var_ligne) == 0 or len(select_var_colonne) == 0)

    if condition:
        st.write("Bien vouloir sélectionner au moins deux variables quantitatives")
    else:
        with col3:
            st.divider()
            st.subheader("Test du Khi 2")
            for ligne in select_var_ligne:
                for colonne in select_var_colonne:
                    resultats = khi2(st.session_state["data"],ligne,colonne)
                    st.dataframe(resultats[0])
                    st.write("{} cellules ont (a) un effectif théorique onférieur à 5".format(int(resultats[1])))
                    add_df_to_doc(resultats[0], analyses, "Association entre {} et {}".format(ligne,colonne))

        with col4:
            st.divider()
            st.subheader("Graphiques")
            for ligne in select_var_ligne:
                for colonne in select_var_colonne:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    df_plot = (st.session_state["data"][ligne]
                               .groupby(st.session_state["data"][colonne])
                               .value_counts(normalize=True)
                               .rename("frequency")
                               .to_frame()
                               .reset_index()
                               )
                    sns.barplot(
                        x=ligne,
                        y="frequency",
                        hue=colonne,
                        data=df_plot,
                        width=0.7
                    )
                    plt.xlabel(ligne)
                    plt.ylabel("Frequency (%)")
                    plt.title("{} VS {}".format(colonne,ligne));

                    buffer = io.BytesIO()

                    plt.savefig(buffer)

                    analyses.add_picture(buffer)
                    st.pyplot(fig)

                    # Cleanup plot
                    plt.close(plt.gcf())
                    plt.clf()

        # Bouton d'enregistrement des analyses
        buffer = io.BytesIO()
        bio = io.BytesIO()
        analyses.save(bio)
        resultats_analyses = bio.getvalue()
        with zipfile.ZipFile(buffer, "x") as zip:
            zip.writestr("associations.docx", resultats_analyses)

        try:
            st.sidebar.divider()
            st.sidebar.write("Télécharger les résultats des analyses")
            st.sidebar.download_button(
                label="Télécharger au format Word :arrow_down:",
                data=buffer.getvalue(),
                file_name="resultats.zip",
                mime="application/zip",
                type="primary",
                disabled=condition
            )
        except:
            st.sidebar.divider()
            st.sidebar.button(
                label="Télécharger",
                disabled=True
            )
