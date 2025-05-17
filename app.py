import io
import os
import streamlit as st
import pandas as pd
import zipfile
import seaborn as sns
import matplotlib.pyplot as plt
from docx import Document
from streamlit import session_state
from packages.functions import add_df_to_doc, khi2, anova, repeated_anova, correlation, reliability, \
    optimum_reliability, validity
from packages.myclasses import MakeAnalysis


#TODO: prendre en charge le traitement de certaines colonnes, notamment la transformation du séparateur
# décimal "," et "."

#Configuration de la page
st.set_page_config(layout="wide",
                   page_icon="📉",
                   page_title="xatix"
                   )

#Liste des analyses
list_analysis = {
    "Association":["Chi square"],
    "Correlation":["Pearson", "Spearman"],
    "Comparison of means":None,
    "scales":None,
    "Multiple Comparisons":None
}

cwd = os.getcwd()
dataset_example = dict()
dataset_example["Association"]                   = os.path.join(cwd,"data","khi2.xlsx")
dataset_example["Correlation"]                   = os.path.join(cwd,"data","corr.xlsx")
dataset_example["Comparison of means"]           = os.path.join(cwd,"data","comp_means.xlsx")
dataset_example["Multiple Comparisons"]          = os.path.join(cwd,"data","multcomp.xlsx")
dataset_example["Scale (Reliability & Validity)"]= os.path.join(cwd,"data","scale.xlsx")


#Jeu de données initial :
#TODO: Coder l'importation et la sauvegarde des jeux de données



# Page d'accueil

st.sidebar.title("Menu")

menu = st.sidebar.radio(
    "Choose an option",
    ["Association",
     "Correlation",
     "Comparison of means",
     "Multiple Comparisons",
     "Scale (Reliability & Validity)",
     "About"]
)

if menu != "About":
    st.title("Data analysis app")

if "data" not in session_state:
    st.session_state["data"] = pd.DataFrame()

if menu in ("Association","Correlation",
            "Comparison of means","Multiple Comparisons", "Scale (Reliability & Validity)"):
    st.header("Data set")  # Title of the section

    uploaded_file = st.file_uploader("Import your data", type=["xlsx","xls", "csv"])
    if uploaded_file != None :
        data = uploaded_file.getvalue()
        try:
            st.session_state["data"] = pd.read_excel(data)

        except TypeError:
            st.session_state["data"] = pd.read_csv(data)

        except ValueError:
            st.session_state["data"] = pd.read_csv(data)

        except NameError:
            st.session_state["data"] = pd.DataFrame()
            st.write("Upload a data set")
    else:
        st.write("Below is an example of data set properly formatted")
        st.session_state["data"] = pd.read_excel(dataset_example[menu])

    st.dataframe(st.session_state["data"], use_container_width=True, hide_index=True)  # Display data

    if not st.session_state["data"].empty:
        list_vars = st.session_state["data"].columns  # Columns of the data set
        num_vars = [var for var in list_vars if st.session_state["data"][var].dtype != "O"]  # Numerical variables
        cat_vars = [var for var in list_vars if st.session_state["data"][var].dtype == "O"]  # Categorical variables
        discrete_vars = [var for var in list_vars if st.session_state["data"][var].dtype == "int"]  # Discrete variables

    else :
        list_vars, num_vars,cat_vars,discrete_vars = list(),list(),list(),list()

    st.divider()  # Horizontal line


# ==================== Multiple Comparisons ====================
if menu == "Multiple Comparisons":

    st.header("Comparing groups and between time periods")


    st.header("Analyses")  # Title of the section

    st.divider()  # Horizontal Line
    # 4 columns that embed the selectbox-es and allow to choose the analyses and variables
    col1, col2, col3 = st.columns(3)
    analyses = Document()

    with col1:

        def initialize_buffer_doc():
            # Creating a document
            analyses = Document()

        # Selectbox to choose the group var
        select_group = st.selectbox(
            "Group's Variable:",
            cat_vars,
            on_change=initialize_buffer_doc,
            key="_group"
        )

    with col2:
        # Selectbox to choose var designating the time period
        select_time = st.selectbox(
            "Time period's variable:",
            [var for var in cat_vars if var !=select_group],
            on_change=initialize_buffer_doc,
            key="_time"
        )

    with col3:
        select_dependent = st.multiselect(
            "Dependent(s) Variable(s):",
            num_vars,
            on_change=initialize_buffer_doc,
            key="_dependent"
        )

    st.divider()

    # Carrying out  the analyses
    results = pd.DataFrame({"": ["No results to display"]})

    col4, col5 = st.columns(2)

    condition = (select_group==None) or (select_time==None) or len(select_dependent)==0

    with col4:
        st.subheader("Results")
        st.divider()

        if not condition:

            # Comparisons between groups
            st.markdown("* ***Comparisons between groups***")

            for time in st.session_state["data"][select_time].unique():
                st.subheader("Time period {} ".format(time))
                analyses.add_paragraph("Time period {} ".format(time))
                data_time = st.session_state["data"][st.session_state["data"][select_time] == time]
                ma = MakeAnalysis(data_time, analyses)
                for val in select_dependent:
                    st.write(val)

                    sortie = ma.anova(select_group, val, analyses)

                    st.write("Testing normality of data ({}) and homocedasticity (Bartlett) : ".format(sortie[3]))
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

                    st.write("Testing normality of data with ({}) and homocedasticity (Bartlett) : ".format(sortie[3]))
                    st.dataframe(sortie[0], use_container_width=True, hide_index=True)
                    st.write("Test de comparaison ({}) : ".format(sortie[4]))
                    st.dataframe(sortie[1], use_container_width=True, hide_index=True)
                    if sortie[4] in ["friedman", "anova"]:
                        st.write("Post hoc")
                        st.dataframe(sortie[6], use_container_width=True)

            analyses = sortie[5]
            bio = io.BytesIO()
            analyses.save(bio)
            resultats_analyses = bio.getvalue()
            graphiques = dict()

    with col5:
        st.subheader("Figures")
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
                    plt.title("Time period {} : {}".format(time, val))

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
                    plt.title("Group {} : {}".format(gr, val))

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
        st.sidebar.write("Download")
        st.sidebar.download_button(
            label="Download :arrow_down:",
            data=buf.getvalue(),
            file_name="resultats.zip",
            mime="application/zip",
            type="primary",
            disabled=(sortie == None)
        )
    else:
        st.sidebar.divider()
        st.sidebar.button(
            label="Download",
            disabled=True
        )

# ==================== Comparing means ====================
elif menu == "Comparison of means":
    st.header("Comparisons between groups")


    st.header("Analyses")  # Title of the section

    # 4 columns that embed the selectbox-es for choosing the types of analyse and variables
    col1, col2, col3 = st.columns(3)
    st.divider()  # Horizontal Line
    analyses = Document()

    with col1:

        def initialize_buffer_doc():
            # Document in session_state
            analyses = Document()

        # Selectbox to choose the group var
        select_type_comp = st.selectbox(
            "Type of comparison:",
            ("Independent Groups", "Pairwise"),
            on_change=initialize_buffer_doc,
            key="_type_comp"
        )

    with col2:
        if select_type_comp == "Independent Groups":
            label = "Group's Variable"
        else:
            label = "Time Period Variable"

        # Selectbox to choose the group var
        select_group = st.selectbox(
            label,
            [var for var in cat_vars],
            on_change=initialize_buffer_doc,
            key="_time"
        )

    with col3:

        select_dependent = st.multiselect(
            "Dependent Variable(s):",
            num_vars,
            on_change=initialize_buffer_doc,
            key="_dependent"
        )

    st.divider()

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results to display"]})

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
                    if select_type_comp == "Independent Groups":
                        sortie = anova(st.session_state["data"], select_group, val, analyses)
                    else:
                        sortie = repeated_anova(st.session_state["data"], select_group, val, analyses)

                    st.write("Testing normality of data ({}) and homocedasticity (Bartlett) : ".format(sortie[3]))
                    st.dataframe(sortie[0], use_container_width=True, hide_index=True)
                    st.write("Comparing ({}) : ".format(sortie[4]))
                    st.dataframe(sortie[1], use_container_width=True, hide_index=True)
                    if sortie[4] in ["kruskal", "anova", 'friedman']:
                        st.write("Post hoc analysis")
                        try:
                            st.dataframe(sortie[6], use_container_width=True)
                        except:
                            st.write("No post hoc shall be done")
                    analyses = sortie[5]

                except:
                    st.write("An error occured!")

    with col5:
        bio = io.BytesIO()
        analyses.save(bio)
        resultats_analyses = bio.getvalue()
        graphiques = dict()
        st.subheader("Figures")
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
        st.sidebar.write("Download")
        st.sidebar.download_button(
            label="Download (.docx) :arrow_down:",
            data=buf.getvalue(),
            file_name="resultats.zip",
            mime="application/zip",
            type="primary",
            disabled=(sortie == None)
        )
    except:
        st.sidebar.divider()
        st.sidebar.button(
            label="Download",
            disabled=True
        )

# ==================== Correlations ====================
elif menu == "Correlation":
    st.header("Correlation between variables")

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
    st.subheader("Results")

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results to display"]})

    col2, col3 = st.columns(2)

    condition = len(select_vars) < 2

    if condition:
        st.write("Choose at least two(2) variables")
    else:
        corr_pear = correlation(st.session_state["data"][select_vars], "pearson", "Correlation map : Pearson")
        # Spearman
        corr_sp = correlation(st.session_state["data"][select_vars], "spearman", "Correlation map : Spearman")

        with col2:
            st.divider()
            # Pearson
            st.subheader("Shapiro-Wilk test (normality) : p-value")
            st.dataframe(corr_pear[0],hide_index=True)

            st.subheader("Pearson's Correlation Coefficient")
            st.dataframe(corr_pear[1])

            st.subheader("Spearman's Correlation Coefficient")
            st.dataframe(corr_sp[1])

            add_df_to_doc(corr_pear[0], analyses, "Normality")
            add_df_to_doc(corr_pear[1], analyses, "Pearson's Correlation")
            add_df_to_doc(corr_sp[1], analyses, "Spearman Correlation")


        with col3:
            st.divider()

            st.subheader("Figures ")
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
        st.sidebar.write("Download")
        st.sidebar.download_button(
            label="Download (.docx) :arrow_down:",
            data=buffer.getvalue(),
            file_name="resultats.zip",
            mime="application/zip",
            type="primary",
            disabled=condition
        )
    except:
        st.sidebar.divider()
        st.sidebar.button(
            label="Download",
            disabled=True
        )

# ==================== Associations ====================
elif menu == "Association":
    st.header("Analysis of associations ")

    st.divider()  # Ligne horizontale
    analyses = Document()

    def initialize_buffer_doc():
        # Création d'un document mois en mémoire dans session_state
        analyses = Document()

    col1,col2 = st.columns(2)

    with col1:
        select_var_ligne = st.multiselect(
            "Row Variable(s):",
            cat_vars,
            on_change=initialize_buffer_doc,
            key="_var_ligne"
        )

    with col2:
        select_var_colonne = st.multiselect(
            "Column Variable(s):",
            [var for var in cat_vars if var not in select_var_ligne],
            on_change=initialize_buffer_doc,
            key="_var_colonne"
        )



    st.subheader("Results")

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results to display"]})

    col3, col4 = st.columns(2)

    condition = (len(select_var_ligne) == 0 or len(select_var_colonne) == 0)

    if condition:
        st.write("Choose at least two(2) variables")
    else:

        st.divider()
        st.subheader("Figures")
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
                plt.title("{} VS {}".format(colonne, ligne));

                buffer = io.BytesIO()

                plt.savefig(buffer)

                analyses.add_picture(buffer)
                st.pyplot(fig)

                # Cleanup plot
                plt.close(plt.gcf())
                plt.clf()

        st.divider()
        st.subheader("Chi Square Test")
        for ligne in select_var_ligne:
            for colonne in select_var_colonne:
                resultats = khi2(st.session_state["data"],ligne,colonne)
                st.dataframe(resultats[0])
                st.write("There is (are) {} cell(s) with a theoretical frequency lower than 5".format(int(resultats[1])))
                add_df_to_doc(resultats[0], analyses, "Association between {} et {}".format(ligne, colonne))
        analyses.add_paragraph("HINT:")
        if resultats[1]:
            if resultats[3] < 0.001: p="<0.001"
            else: p = str(round(resultats[3],3))[:5]
            analyses.add_paragraph(f"Since {resultats[1]} cell(s) have expected frequency(ies) below 5, the assumptions of the Chi-square test are violated. Consequently, the test results may not be considered statistically valid.")
            if resultats[3] < 0.001:
                analyses.add_paragraph(f"It is preferable to use Fisher’s exact test. With a p-value less than 0.001, we can conclude that the association between the two variables is statistically highly significant.")
            elif resultats[3]<0.05:
                analyses.add_paragraph(f"It is preferable to use Fisher’s exact test. With a p-value estimated at {p}, we can conclude that the association between the two variables is statistically significant at the 5% level.")
            else:
                analyses.add_paragraph(
                    f"It is preferable to use Fisher’s exact test. With a p-value estimated at {resultats[3]}, we can conclude that the association between the two variables is not statistically significant at the 5% level.")
        else:
            if resultats[2] < 0.001:
                analyses.add_paragraph(
                    f"With a p-value less than 0.001, we can conclude that the association between the two variables is highly significant.")
            if resultats[2]<0.05:
                analyses.add_paragraph(f"With a p-value estimated at {resultats[2]}, we can conclude that the association between the two variables is statistically significant at the 5% level.")
            else:
                analyses.add_paragraph(
                    f"With a p-value estimated at {resultats[2]}, we can conclude that the association between the two variables is not statistically significant at the 5% level.")


        # Bouton d'enregistrement des analyses
        buffer = io.BytesIO()
        bio = io.BytesIO()
        analyses.save(bio)
        resultats_analyses = bio.getvalue()
        with zipfile.ZipFile(buffer, "x") as zip:
            zip.writestr("associations.docx", resultats_analyses)

        try:
            st.sidebar.divider()
            st.sidebar.write("Download")
            st.sidebar.download_button(
                label="Download (.docx) :arrow_down:",
                data=buffer.getvalue(),
                file_name="results.zip",
                mime="application/zip",
                type="primary",
                disabled=condition
            )
        except:
            st.sidebar.divider()
            st.sidebar.button(
                label="Download",
                disabled=True
            )



# ==================== Reliability ====================
elif menu == "Scale (Reliability & Validity)":
    st.header("Reliability")

    st.divider()  # Horizontal line
    analyses = Document()

    if not st.session_state["data"].empty:
        list_vars = st.session_state["data"].columns  # Columns of the data set
        discrete_vars = [var for var in list_vars if st.session_state["data"][var].dtype != "O"]  # Numerical variables

    else :
        discrete_vars = list()

    def initialize_buffer_doc():
        analyses = Document()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Select items")

        select_vars = st.multiselect(
            "Items :",
            discrete_vars,
            on_change=initialize_buffer_doc,
            key="_analysis"
        )

    condition = len(select_vars) < 2

    with col2:
        st.subheader("Choose the analysis to be carried on")
        select_analysis = st.selectbox(
            "Analysis :",
            ["Reliability", "Optimisation of the reliability", "Validity"],
            on_change=initialize_buffer_doc,
            key="_items"
        )

    st.subheader("Results")

    # Réalisation de l'analyse
    results = pd.DataFrame({"": ["No results"]})

    if condition:
        st.write("Choose at least two(2) items")
    elif select_analysis=="Reliability":
        results = reliability(st.session_state["data"], select_vars, analyses)
        st.write("Cronbach's Alpha : {}".format(results[0][0]))
        st.write("Alpha without some items")
        st.dataframe(results[1], hide_index=True, use_container_width=True)

        # Bouton d'enregistrement des analyses
        buffer = io.BytesIO()
        bio = io.BytesIO()
        analyses.save(bio)
        resultats_analyses = bio.getvalue()
        with zipfile.ZipFile(buffer, "x") as zip:
            zip.writestr("reliability.docx", resultats_analyses)

        try:
            st.sidebar.divider()
            st.sidebar.write("Download")
            st.sidebar.download_button(
                label="Download (.docx) :arrow_down:",
                data=buffer.getvalue(),
                file_name="results.zip",
                mime="application/zip",
                type="primary",
                disabled=condition
            )
        except:
            st.sidebar.divider()
            st.sidebar.button(
                label="Download",
                disabled=True
            )

    elif select_analysis == "Optimisation of the reliability":
        results = optimum_reliability(st.session_state["data"], select_vars, analyses)
        for i in range(len(results[0])):
            st.write(results[0][i])
            st.write("Valeurs de alpha en cas d'exclusion des items")
            st.dataframe(results[1][i], hide_index=True, use_container_width=True)

            # Bouton d'enregistrement des analyses
            buffer = io.BytesIO()
            bio = io.BytesIO()
            analyses.save(bio)
            resultats_analyses = bio.getvalue()
        with zipfile.ZipFile(buffer, "x") as zip:
            zip.writestr("Optimisation_fiabilité.docx", resultats_analyses)

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
    elif select_analysis=="Validity":
        results = validity(st.session_state["data"], select_vars, analyses)

        st.dataframe(results, hide_index=True)

        #st.write("Matrice des corrélation : rotation=varimax")
        # st.dataframe(results[1])

        # Bouton d'enregistrement des analyses
        buffer = io.BytesIO()
        bio = io.BytesIO()
        analyses.save(bio)
        resultats_analyses = bio.getvalue()
        with zipfile.ZipFile(buffer, "x") as zip:
            zip.writestr("fiabilité.docx", resultats_analyses)

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
if menu=="About":
    st.header("About the author")

    st.markdown('<div '
                'style="text-align: justify;">'
                """My name is Adrien Kouanda, and I am a statistician and data scientist. I studied statistics from 2004 to 2008 at the Sub-Regional Institute of Statistics and Applied Economics in Cameroon.
                 Since 2008, I have been working at the Ministry of Economy, Planning, and Regional Development in Cameroon, where I contribute by providing data-driven insights and recommendations based on the analysis of public investment performance.
                 I started out as a statistician and gradually transitioned into data science as I developed skills in Python, machine learning, and cloud tools.
                 I have completed several specialized programs in data science and AI, including hands-on labs with WorldQuant University, and I’ve built projects like diagnostically predicts whether or not a patient has diabetes, based on certain diagnostic measurements.
                 """
                '</div>', unsafe_allow_html=True)

    st.markdown('<div '
                'style="text-align: justify;">'

                 """ Over the years, I have frequently been approached—both in person and online—by medical interns, graduate and doctoral students from various fields such as health, human resources, marketing, and economics, as well as by researchers. They often seek support in analyzing their data. I’m also active on several platforms, including comeup.com (under the name Adrien DAK).
                    These recurring experiences inspired me to design an application that simplifies the process of research data analysis, while guiding users in understanding and interpreting their results.
                """

                '</div>', unsafe_allow_html=True)

    st.markdown('<div '
                'style="text-align: justify;">'

                """ The version presented here includes only a subset of the features planned for the final application. One of the key functionalities will be the ability to identify factors associated with a given phenomenon using logistic regression, complete with interpretation of odds ratios.
                    This application was built using the Streamlit framework and leverages the strengths of both Python and R to deliver robust statistical analysis.
               """

                '</div>', unsafe_allow_html=True)

