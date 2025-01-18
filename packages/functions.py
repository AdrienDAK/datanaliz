#from xml.dom.minidom import Document
from docx import  Document
import scipy.stats as stat
import pandas as pd
import seaborn as sns
from io import BytesIO
import numpy as np
import pingouin as pg
import textwrap
import matplotlib.pyplot as plt
from numpy.f2py.auxfuncs import isstring
from scikit_posthocs import posthoc_dunn as pdunn
from scikit_posthocs import posthoc_ttest as pttest
from scikit_posthocs import posthoc_nemenyi_friedman as pfriedman

def affiche_pvalue(pv):
    """
    :param pv: Une valeur décimale telle qu'une p-value
    :return: une valeur décimale arrondie à 3 chiffres si pv est ≥0.001 ou le caractère <0.001 dans
        le cas contraire. pv reste inchangé s'il est un caractère.
    """
    try:
        if float(pv) < 0.001:
            return "<0.001"
        else :
            return round(float(pv), 3)

    except:
        return pv

def add_df_to_doc(df,doc, title):
    """
        Cette fonction permet d'ajouter le dataframe df dans le document ouvert
        :param df: le dataframe que l'on souhaite ajouter dans le document Word
        :param doc: le chemin vers le document dans lequel l'on veut ajouter le tableau
        :return: La fonction ne retourne pas de résultat
        """

    p = doc.add_paragraph(title)

    # add a table to the end and create a reference variable
    # extra row is so we can add the header row
    t = doc.add_table(df.shape[0] + 1, df.shape[1])

    # add the header rows.
    for j in range(df.shape[-1]):
        t.cell(0, j).text = df.columns[j]

    # add the rest of the data frame
    for i in range(df.shape[0]):
        for j in range(df.shape[-1]):
            t.cell(i + 1, j).text = str(df.values[i, j])

    p = doc.add_paragraph(""" """)


def add_analyses_to_doc_disk(new_analyses,path_to_doc, title):
    """
    Cette fonction permet d'ajouter le dataframe df dans le document enregistré sur le disque dont le chemin est path_to_doc
    :param doc: le document docx contenant les éléments que l'on souhaite ajouter
    :param path_to_doc: le chemin vers le document dans lequel l'on veut ajouter les éléments
    :return: La fonction ne retourne pas de résultat. Il sauvegarde sous le même nom que le document existant
            au chemin path_to_doc
    """

    # open an existing document
    doc = Document(path_to_doc)

    p = doc.add_paragraph(title)

    # add a table to the end and create a reference variable


    # add the elements.
    for element in new_analyses.element.body:
        doc.element.body.append(element)

    p = doc.add_paragraph(""" """)

    # save the doc
    doc.save(path_to_doc)


def khi2(df,var_ligne, var_colonne):
    """ Cette fonction réalise le test du Chi 2 entre deux variables : colonne et ligne
            Le résultat est un tableau croisé dans lequel l'on a en colonnes les modalités
                de la variable colonne et en lignes les variables lignes et leurs modalités respectives.

            Les paramètres sont les suivants :
                - df : un DataFrame
                - var_colonne : une des colonnes de 'df', correspondant à une variable qualitative
                - ligne : une des colonnes de 'df', différente de la précédente qualitative également

            Le résultat de la fonction est un dataframe comportant le tableau croisé des 2 variables et deux autres colonnes
            affichant le nombre de degrés de liberté et la p-value du test

        """

    d = df.copy()
    tableau = pd.DataFrame()
    colonne_total = list()
    totaux = d[var_ligne].value_counts()

    nouv_vals = dict()

    presence_oui = False
    presence_yes = False

    for modalite in d[var_ligne].astype(str):
        if 'Oui' in modalite or 'oui' in modalite:
            presence_oui = True
        if 'Yes' in modalite or 'yes' in modalite:
            presence_yes = True

    if presence_oui or presence_yes:
        for modalite in d[var_ligne].astype(str):
            nouv_vals[modalite] = '{}-{}'.format(var_ligne, modalite)

    try:
        d[var_ligne] = d[var_ligne].replace(nouv_vals)
    except:
        pass

    cont = d[[var_ligne, var_colonne]].pivot_table(index=var_ligne, columns=var_colonne, aggfunc=len).fillna(
        0).copy()
    st_chi2, st_p, st_dof, st_exp = stat.chi2_contingency(cont)
    # Ajout des colonnes Stat Chi-2 (valeur de la stat), Nombre de DL et P-value

    #Test exact de Fisher
    stats = importr('stats')
    p_fisher = stats.fisher_test(cont.to_numpy())[0][0]

    chi2 = [''] * len(cont)
    chi2[0] = str(round(st_chi2, 3))

    DL = [''] * len(cont)
    DL[0] = st_dof

    PV = [''] * len(cont)
    PV[0] = ".".join([elt[:4] for elt in str(round(st_p, 4)).split(".")])

    cont['TOTAL'] = cont.sum(axis=1)
    cont = cont.astype(int)
    tableau = pd.concat([cont, tableau])

    total_general = sum(list(cont.sum())[:-1])
    nb_eff_5 = 0
    for i in list(cont.sum())[:-1]:
        for j in list(cont["TOTAL"]):
            nb_eff_5 += (i * j / total_general < 5)
    nb_eff_5 = nb_eff_5 * 100 / (len(set(d[var_ligne])) * len(set(d[var_colonne])))

    tableau['Stat Khi-2'] = chi2
    tableau['DL'] = DL
    tableau['P-value'] = PV

    if nb_eff_5:
        PV_fisher = [''] * len(cont)
        PV_fisher[0] = ".".join([elt[:4] for elt in str(round(p_fisher, 4)).split(".")])
        tableau['Test de Fisher (pv)'] = PV_fisher


    return (tableau, nb_eff_5, p_fisher)

def anova(data,groupes,valeurs, input_report):
    """ Cette fonction réalise le test de l'analyse de la variance entre une variable indépendante qualitative et une variable dépendante quantitative
    		Le résultat est un tableau présentant la moyenne de la variable dépendante pour chaque modalité.

    		Lorsque la différence entre les modalités est significative, une analyse post-hoc permet de tester les différences entre modalités deux à deux
    		et de déterminer quelles modalités sont significativement différentes l'une de l'autre.

    		Les paramètres sont les suivants :
    			- data : un DataFrame
    			- groupes : une des colonnes de 'data', correspondant à une variable qualitative
    			- valeurs : une des colonnes de 'data' correspondant à une variables quantitative
    			- langue : 'français' ou 'anglais', désigne la langue dans laquelle seront formulés les commentaires/interprétations des résultats
    			- path : le chemin vers le dossier où sera enregistré le fichier Word des résultats
    			- dossier_images : chemin vers le dossier où sera enregistrée le graphique généré par le test

    		Le résultat de la fonction est une liste [nom_analyse, list_graphiques] :
    			- nom_analyse est à la fois le nom du dossier contenant le fichier des analyses et le nom dudit fichier
    			- list_graphiques est la liste des noms des graphiques

    	"""
    comment = list()
    graphiques = []

    test = {'kruskal': stat.kruskal,
            'anova': stat.f_oneway,
            "mannwhitney":stat.mannwhitneyu,
            "student":stat.ttest_ind}

    ################### Tests de normalité et d'homocédasticité #######################
    # Test de normalité de la variable dépendante
    # Si la taille de l'échantillon est inférieure ou égale à 50, l'on applique le test de Shapiro-Wilk
    # Au-delà de 50, l'on utilise le test de Kolmogorov-Smornov
    test_norm = ""
    if len(data)/len(data[groupes].unique()) <= 50:
        test_norm = "Shapiro-Wilk"
        p_value_normalite = affiche_pvalue(stat.shapiro(data[valeurs])[1])

    else:
        test_norm = "Kolmogorov"
        p_value_normalite = affiche_pvalue(stat.kstest(data[valeurs], 'norm')[1])




    p = input_report.add_paragraph('Boites à moustaches (variables quantitatives)')
    l = list(set(data[groupes]))
    l.sort()
    arrays = [list(data[data[groupes] == groupe][valeurs]) for groupe in l]

    buffer = BytesIO()
    bp = plt.boxplot(arrays, labels=l, showmeans=True, patch_artist=True)
    plt.title("{}".format(valeurs))
    for box in bp["boxes"]:
        box.set_facecolor('lightblue')

    plt.savefig(buffer)

    # hand buffer to python-docx
    input_report.add_picture(buffer)


    # Cleanup plot
    plt.close(plt.gcf())
    plt.clf()


    p_value_homocedast = affiche_pvalue(stat.bartlett(*arrays)[1])

    norm_homocedastic = pd.DataFrame({"normalité": [p_value_normalite], "homocédasticité": [p_value_homocedast]})


    table = input_report.add_table(rows=1, cols=2, style='LightShading-Accent1')

    hdr_cells = table.rows[0].cells

    hdr_cells[0].text = 'p normalité'
    hdr_cells[1].text = 'p homocédasticité'
    row_cells = table.add_row().cells
    row_cells[0].text = str(p_value_normalite)
    row_cells[1].text = str(p_value_homocedast)

    if len(data) <= 50:
        commentaires = [
            "Le test de Shapiro est utilisé pour vérifier la normalité de la variable dépendante.",
            "Le test de Bartlett est utilisé pour vérifier l'homocédasticité (égalité des variance entre groupes)."
        ]
    else:
        commentaires = [
            "Le test de Kolmogorov-Smirnov est utilisé pour vérifier la normalité de la variable dépendante.",
            "Le test de Bartlett est utilisé pour vérifier l'homocédasticité (égalité des variance entre groupes)."
        ]

    if len(list(data[groupes].unique())) == 2:
        other_comment = [
            "Le test de Student repose sur trois hypothèses :",
            "- la normalité de la variable dépendante ;",
            "- l'homocédasticité (égalité entre les variances des groupes) ;",
            "- l'indépendance entre les groupes.",
            "L'on va s'atteler à vérifier les deux premières hypothèses."
        ]
        if isinstance(p_value_normalite, str) or  isinstance(p_value_homocedast, str):
            key = 'mannwhitney'
        elif p_value_normalite > 0.05 and p_value_homocedast > 0.05:
            key = "student"
        else:
            key = 'mannwhitney'

    else:
        other_comment = [
            "L'anova paramétrique' repose sur trois hypothèses :",
            "- la normalité de la variable dépendante ;",
            "- l'homocédasticité (égalité entre les variances des groupes) ;",
            "- l'indépendance entre les groupes.",
            "L'on va s'atteler à vérifier les deux premières hypothèses."
        ]

        if not (isinstance(p_value_normalite, str) or  isinstance(p_value_homocedast, str)) and p_value_normalite > 0.05 and p_value_homocedast > 0.05:
            key = "anova"
        else:
            key = 'kruskal'

    for com in other_comment:
        commentaires.append(com)


    for com in commentaires:
            comment.append(com + "|")
            p = input_report.add_paragraph(com)

    if (not isinstance(p_value_normalite, str)) and  (not isinstance(p_value_homocedast, str)) and p_value_normalite > 0.05 and p_value_homocedast > 0.05:
        commentaires.append(
            "Ces conditions sont respectées. L'on utilisera donc le test : {}".format(key)
        )
    else:
        commentaires.append(
            "Ces conditions ne sont pas respectées. L'on utilisera donc le test : {}".format(key)
        )



    #################### Comparaison des groupes  #########################################

    # TODO: address the matter pertaining to the comments of the principal comparison
    comment = []
    donnees_anova = []
    lignes = []
    moyenne = []
    ecart_type = []
    minimum = []
    median = []
    maximum = []
    l = list(data[groupes].unique())
    l.sort()
    for gr in l:
        donnees_anova.append(list(data[data[groupes] == gr][valeurs]))
        lignes.append(gr)
        moyenne.append(round(np.mean(list(data[data[groupes] == gr][valeurs])),3))
        ecart_type.append(round(np.std(list(data[data[groupes] == gr][valeurs])),3))
        minimum.append(round(np.min(list(data[data[groupes] == gr][valeurs])),3))
        median.append(round(np.median(list(data[data[groupes] == gr][valeurs])),3))
        maximum.append(round(np.max(list(data[data[groupes] == gr][valeurs])),3))

    valeurs_par_groupe_anova = pd.DataFrame({groupes: lignes, 'Moyenne': moyenne, 'Ecart-type': ecart_type, 'Minimum': minimum,
                                       'Médiane': median, 'Maximum': maximum})

    anova = [''] * len(valeurs_par_groupe_anova)
    anova[0] = round(test[key](*donnees_anova)[0], 3)

    PV = [''] * len(valeurs_par_groupe_anova)
    PV[0] = affiche_pvalue(test[key](*donnees_anova, )[1])

    valeurs_par_groupe_anova['Stat'] = anova
    valeurs_par_groupe_anova['P-value'] = PV


    # Ajout du tableau dans le document word
    p = input_report.add_paragraph('')
    p = input_report.add_paragraph(
        'Comparaison : variable {} en fonction de la variable {}'.format(valeurs, groupes))

    table = input_report.add_table(rows=1, cols=valeurs_par_groupe_anova.shape[1], style='LightShading-Accent1')
    col_names = list(valeurs_par_groupe_anova.columns)

    lign_names = list(valeurs_par_groupe_anova.index)
    hdr_cells = table.rows[0].cells

    for i in range(len(col_names)):
        hdr_cells[i].text = col_names[i]

    for lign in valeurs_par_groupe_anova.values:
        row_cells = table.add_row().cells
        for i in range(len(lign)):
            row_cells[i].text = str(list(lign)[i])

    p = input_report.add_paragraph('')
    if round(test[key](*donnees_anova)[1], 3) < 0.05:
        com = "La p-value du test {} est inférieure à 5%. L'on a donc de bonnes raisons de croire que certains groupes ont des moyennes différentes.".format(
            key)
        p = input_report.add_paragraph(com)
        comment.append(com)

        if len(list(data[groupes].unique())) <= 2:
            # Commentaires
            com = "La p-value du test {} est inférieure à 5%. L'on a donc de bonnes raisons de croire que certains groupes ont des moyennes différentes.Etant donné que la variable indépendante n'a que deux modalités, réaliser une analyse post-hoc n'a aucun sens.".format(
                key)
            p = input_report.add_paragraph(com)
            comment.append(com)

        else:
            com = "L'on doit donc effectuer une analyse post hoc pour déterminer les groupes dont les moyennes sont différentes"
            p = input_report.add_paragraph(com)
            comment.append(com)
            p = input_report.add_paragraph('')

            if key == 'kruskal':
                # p = input_report.add_paragraph('Analyse post hoc : test de Dunn')
                # Commentaires
                comment.append(
                    "La p-value est inférieure à 5%. L'on a donc de bonnes raisons de croire que certains groupes ont des moyennes différentes.")
                comment.append(
                    "L'on doit à présent effectuer une analyse post hoc pour déterminer les groupes dont les moyennes sont différentes.")
                comment.append("Le test de Dunn est utilisé pour l'analyse post hoc")
            else:
                # Commentaires
                comment.append(
                    "La p-value est inférieure à 5%. L'on a donc de bonnes raisons de croire que certains groupes ont des moyennes différentes.")
                comment.append(
                    "L'on doit à présent effectuer une analyse post hoc pour déterminer les groupes dont les moyennes sont différentes.")
                comment.append("Analyse post hoc : t-test")

                p = input_report.add_paragraph('Analyse post hoc : t-test')

            ##### Analyse post-hoc ##########################################
            l = list(data[groupes].unique())
            post_hoc_res = pdunn(data, val_col=valeurs, group_col=groupes, p_adjust="bonferroni")


            for i in range(len(l)):
                if i == len(l) - 1:
                    pass
                else:
                    for j in range(i + 1, len(l)):
                        lignes = [l[i], l[j]]
                        moyenne = [round(np.mean(list(data[data[groupes] == l[i]][valeurs]))),
                                   round(np.mean(list(data[data[groupes] == l[j]][valeurs])))]
                        ecart_type = [round(np.std(list(data[data[groupes] == l[i]][valeurs]))),
                                      round(np.std(list(data[data[groupes] == l[j]][valeurs])))]
                        minimum = [round(np.min(list(data[data[groupes] == l[i]][valeurs]))),
                                   round(np.min(list(data[data[groupes] == l[j]][valeurs])))]
                        median = [round(np.median(list(data[data[groupes] == l[i]][valeurs]))),
                                  round(np.median(list(data[data[groupes] == l[j]][valeurs])))]
                        maximum = [round(np.max(list(data[data[groupes] == l[i]][valeurs]))),
                                   round(np.max(list(data[data[groupes] == l[j]][valeurs])))]

                        valeurs_par_groupe_post = pd.DataFrame(
                                {groupes: lignes, 'Moyenne': moyenne, 'Ecart-type': ecart_type, 'Minimum': minimum,
                                                'Médiane': median, 'Maximum': maximum})

                        PV = [''] * len(valeurs_par_groupe_post)
                        PV[0] = affiche_pvalue(post_hoc_res[l[i]][l[j]])
                        valeurs_par_groupe_post['P-value'] = PV

                        add_df_to_doc(valeurs_par_groupe_post, input_report, " ")


                        if post_hoc_res[l[i]][l[j]] > 0.05:
                            comment.append("Il n'existe pas différence significative entre {} et {}".format(l[i], l[j]))
                        else:
                            comment.append(
                                "Au seuil de 5%, il existe une différence significative entre {} et {}.".format(l[i],
                                                                                                                l[j]))
            res = post_hoc_res.copy()

            post_hoc_res = pd.DataFrame()
            for col in res.columns:
                try:
                    post_hoc_res[col] = res[col].astype(float).apply(lambda x: affiche_pvalue(x))
                except:
                    post_hoc_res[col] = res[col]

    commentaires = str()
    for com in comment:
        commentaires += com
        input_report.add_paragraph(com)
    comment = commentaires
    comment = comment[:-1]


    try:
        return [norm_homocedastic, valeurs_par_groupe_anova, comment, test_norm, key,input_report,post_hoc_res]
    except:
        return [norm_homocedastic, valeurs_par_groupe_anova, comment,  test_norm, key,input_report]


def repeated_anova(data,time,valeurs, input_report):
    """ Cette fonction réalise le test de l'analyse de la variance à mesures répétées entre une variable indépendante qualitative (temps) et une variable dépendante quantitative
    		Le résultat est un tableau présentant la moyenne de la variable dépendante pour chaque modalité.

    		Lorsque la différence entre les modalités est significative, une analyse post-hoc permet de tester les différences entre modalités deux à deux
    		et de déterminer quelles modalités sont significativement différentes l'une de l'autre.

    		Les paramètres sont les suivants :
    			- data : un DataFrame
    			- time : une des colonnes de 'data', correspondant aux moments des mesures
    			- valeurs : une des colonnes de 'data' correspondant à une variable quantitative
    			- langue : 'français' ou 'anglais', désigne la langue dans laquelle seront formulés les commentaires/interprétations des résultats
    			- path : le chemin vers le dossier où sera enregistré le fichier Word des résultats
    			- dossier_images : chemin vers le dossier où sera enregistré le graphique généré par le test

    		Le résultat de la fonction est une liste [norm_homocedastic, valeurs_par_groupe_anova, comment, analyses, test_norm, key,post_hoc_res] :
    			-
    			-

    	"""
    comment = list()
    graphiques = []

    test = {'friedman': stat.friedmanchisquare,
            'anova': pg.rm_anova,
            "wilcoxon":stat.wilcoxon,
            "student":stat.ttest_rel}

    ################### Tests de normalité et d'homocédasticité #######################
    # Test de normalité de la variable dépendante
    # Si la taille de l'échantillon est inférieure ou égale à 50, l'on applique le test de Shapiro-Wilk
    # Au-delà de 50, l'on utilise le test de Kolmogorov-Smornov
    test_norm = ""
    if len(data)/len(data[time].unique()) <= 50:
        test_norm = "Shapiro-Wilk"
        p_value_normalite = stat.shapiro(data[valeurs])[1]

    else:
        test_norm = "Kolmogorov"
        p_value_normalite = stat.kstest(data[valeurs], 'norm')[1]

    p = input_report.add_paragraph('Boites à moustaches (variables quantitatives)')
    l = list(data[time].unique())
    l.sort()
    arrays = [list(data[data[time] == t][valeurs]) for t in l ]

    buffer = BytesIO()
    bp = plt.boxplot(arrays, labels=l, showmeans=True, patch_artist=True)
    plt.title("{}".format(valeurs))
    for box in bp["boxes"]:
        box.set_facecolor('lightblue')

    plt.savefig(buffer)

    # hand buffer to python-docx
    input_report.add_picture(buffer)

    # Cleanup plot
    plt.close(plt.gcf())
    plt.clf()

    p_value_homocedast = stat.bartlett(*arrays)[1]

    norm_homocedastic = pd.DataFrame({
        "normalité": [affiche_pvalue(p_value_normalite)],
        "homocédasticité": [affiche_pvalue(p_value_homocedast)]})

    table = input_report.add_table(rows=1, cols=2, style='LightShading-Accent1')

    hdr_cells = table.rows[0].cells

    hdr_cells[0].text = 'p normalité'
    hdr_cells[1].text = 'p homocédasticité'
    row_cells = table.add_row().cells
    row_cells[0].text = str(p_value_normalite)
    row_cells[1].text = str(p_value_homocedast)

    if len(data) <= 50:
        commentaires = [
            "Le test de Shapiro est utilisé pour vérifier la normalité de la variable dépendante.",
            "Le test de Bartlett est utilisé pour vérifier l'homocédasticité (égalité des variance entre groupes)."
        ]
    else:
        commentaires = [
            "Le test de Kolmogorov-Smirnov est utilisé pour vérifier la normalité de la variable dépendante.",
            "Le test de Bartlett est utilisé pour vérifier l'homocédasticité (égalité des variance entre groupes)."
        ]

    if len(list(data[time].unique())) == 2:
        other_comment = [
            "Le test de Student repose sur trois hypothèses :",
            "- la normalité de la variable dépendante ;",
            "- l'homocédasticité (égalité entre les variances des moments) ;",
            "- l'indépendance entre les moments.",
            "L'on va s'atteler à vérifier les deux premières hypothèses."
        ]
        if p_value_normalite > 0.05 and p_value_homocedast > 0.05:
            key = "student"
        else:
            key = 'wilcoxon'

    else:
        other_comment = [
            "L'anova paramétrique' repose sur trois hypothèses :",
            "- la normalité de la variable dépendante ;",
            "- l'homocédasticité (égalité entre les variances des moments) ;",
            "- l'indépendance entre les moments.",
            "L'on va s'atteler à vérifier les deux premières hypothèses."
        ]

        if p_value_normalite > 0.05 and p_value_homocedast > 0.05:
            key = "anova"
        else:
            key = 'friedman'

    for com in other_comment:
        commentaires.append(com)

    for com in commentaires:
        comment.append(com + "|")
        p = input_report.add_paragraph(com)

    if p_value_normalite > 0.05 and p_value_homocedast > 0.05:
        commentaires.append(
            "Ces conditions sont respectées. L'on utilisera donc le test : {}".format(key)
        )
    else:
        commentaires.append(
            "Ces conditions ne sont pas respectées. L'on utilisera donc le test : {}".format(key)
        )


    #################### Comparaison des moments  #########################################

    # TODO: address the matter pertaining to the comments of the principal comparison
    comment = []
    donnees_anova = []
    lignes = []
    moyenne = []
    ecart_type = []
    minimum = []
    median = []
    maximum = []
    for gr in list(data[time].unique()):
        donnees_anova.append(list(data[data[time] == gr][valeurs]))
        lignes.append(gr)
        moyenne.append(round(np.mean(list(data[data[time] == gr][valeurs]))))
        ecart_type.append(round(np.std(list(data[data[time] == gr][valeurs]))))
        minimum.append(np.min(list(data[data[time] == gr][valeurs])))
        median.append(np.median(list(data[data[time] == gr][valeurs])))
        maximum.append(np.max(list(data[data[time] == gr][valeurs])))

    valeurs_par_groupe_anova = pd.DataFrame({time: lignes, 'Moyenne': moyenne, 'Ecart-type': ecart_type, 'Minimum': minimum,
                                       'Médiane': median, 'Maximum': maximum})

    anova = [''] * len(valeurs_par_groupe_anova)
    PV = [''] * len(valeurs_par_groupe_anova)

    if key == "anova":
        df = pd.DataFrame()

        for t in list(data[time].unique()):
            df[t] = list(data[data[time] == t][valeurs])
        anova[0] = round(test[key](df)["F"])[0]
        PV[0] = affiche_pvalue(test[key](df)["p-unc"][0])
    else:
        anova[0] = round(test[key](*donnees_anova)[0], 3)
        PV[0] = affiche_pvalue(test[key](*donnees_anova, )[1])

    valeurs_par_groupe_anova['Stat'] = anova
    valeurs_par_groupe_anova['P-value'] = PV


    # Ajout du tableau dans le document word
    p = input_report.add_paragraph('')
    p = input_report.add_paragraph(
        'Comparaison : variable {} en fonction de la variable {}'.format(valeurs, time))

    table = input_report.add_table(rows=1, cols=valeurs_par_groupe_anova.shape[1], style='LightShading-Accent1')
    col_names = list(valeurs_par_groupe_anova.columns)

    lign_names = list(valeurs_par_groupe_anova.index)
    hdr_cells = table.rows[0].cells

    for i in range(len(col_names)):
        hdr_cells[i].text = col_names[i]

    for lign in valeurs_par_groupe_anova.values:
        row_cells = table.add_row().cells
        for i in range(len(lign)):
            row_cells[i].text = str(list(lign)[i])

    p = input_report.add_paragraph('')

    ##### Analyse post-hoc ##########################################

    if key == "anova":
        comment.append("Analyse post hoc : t-test")
        index = list()
        df = data.copy()
        t0 = list(df[time].unique())[0]
        len(df[df[time] == t0])
        for t in list(df[time].unique()):
            for elt in range(len(df[df[time] == t0])):
                index.append(elt)
        df["index"] = index
        post_hoc_res = pg.pairwise_ttests(data=df,within=time,dv=valeurs, subject="index")
    elif key=="friedman":
        comment.append("Analyse post hoc : test de Dunn")
        l = list(data[time].unique())
        post_hoc_res = pdunn(data, val_col=valeurs, group_col=time, p_adjust="bonferroni")

    try:
        add_df_to_doc(post_hoc_res,input_report, " ")
        res = post_hoc_res.copy()
        post_hoc_res = pd.DataFrame()
        for col in res.columns:
            try:
                post_hoc_res[col] = res[col].astype(float).apply(lambda x: affiche_pvalue(x))
            except:
                post_hoc_res[col] = res[col]
    except:
        post_hoc_res = pd.DataFrame({" ": ["Pas d'analyse post hoc"]})


    commentaires = str()
    for com in comment:
        commentaires += com
    comment = commentaires
    comment = comment[:-1]

    try:
        return [norm_homocedastic, valeurs_par_groupe_anova, comment, test_norm, key,input_report,post_hoc_res]
    except:
        return [norm_homocedastic, valeurs_par_groupe_anova, comment, test_norm, key,input_report]

def correlation(data,method,title):
    normalite = pd.DataFrame()
    resultats_corr = pd.DataFrame()

    for var in data.columns:
        normalite[var] = [affiche_pvalue(stat.shapiro(data[var])[1])]

    corr = data.corr(method=method, numeric_only=True)

    # mask the correlation matrix to diagonal
    mask = np.zeros_like(corr, dtype=bool)
    mask[np.triu_indices_from(mask)] = True
    np.fill_diagonal(mask, False)

    fig, ax = plt.subplots(figsize=(10, 5))
    plt.title(title, fontsize=14)

    # Generate heatmap
    heatmap = sns.heatmap(corr,
                          annot=True,
                          annot_kws={"fontsize": 10},
                          fmt='.2f',
                          linewidths=0.5,
                          cmap='RdBu',
                          mask=mask,
                          ax=ax)

    # calculate and format p-values
    p_values = np.full((corr.shape[0], corr.shape[1]), np.nan)
    for i in range(corr.shape[0]):
        for j in range(i + 1, corr.shape[1]):
            x = data.iloc[:, i]
            y = data.iloc[:, j]
            mask = ~np.logical_or(np.isnan(x), np.isnan(y))
            if np.sum(mask) > 0:
                p_values[i, j] = stat.spearmanr(x[mask], y[mask])[1]

    # Create a dataframe object for p_values
    p_values = pd.DataFrame(p_values, columns=corr.columns, index=corr.index)

    # Mask the p values
    mask_pvalues = np.triu(np.ones_like(p_values), k=1)

    # Generate maximum and minimum correlation coefficients for p-value annotation color
    max_corr = np.max(corr.max())
    min_corr = np.min(corr.min())

    # Assign p-value annotations, include asterisks for significance
    for i in range(p_values.shape[0]):
        for j in range(p_values.shape[1]):
            if mask_pvalues[i, j]:
                p_value = p_values.iloc[i, j]
                if not np.isnan(p_value):
                    correlation_value = corr.iloc[i, j]
                    text_color = 'white' if correlation_value >= (max_corr - 0.4) or correlation_value <= (
                            min_corr + 0.4) else 'black'
                    if p_value <= 0.01:
                        # include double asterisks for p-value <= 0.01
                        ax.text(i + 0.5, j + 0.8, f'(p = {p_value:.2f})**',
                                horizontalalignment='center',
                                verticalalignment='center',
                                fontsize=8,
                                color=text_color)
                    elif p_value <= 0.05:
                        # include single asterisk for p-value <= 0.05
                        ax.text(i + 0.5, j + 0.8, f'(p = {p_value:.2f})*',
                                horizontalalignment='center',
                                verticalalignment='center',
                                fontsize=8,
                                color=text_color)
                    else:
                        ax.text(i + 0.5, j + 0.8, f'(p = {p_value:.2f})',
                                horizontalalignment='center',
                                verticalalignment='center',
                                fontsize=8,
                                color=text_color)

    # Customize x-axis labels
    x_labels = [textwrap.fill(label.get_text(), 13) for label in ax.get_xticklabels()]
    ax.set_xticklabels(x_labels, rotation=0, ha="center")

    # Customize y-axis labels
    y_labels = [textwrap.fill(label.get_text(), 13) for label in ax.get_yticklabels()]
    ax.set_yticklabels(y_labels, rotation=0, ha="right")

    buffer = BytesIO()

    plt.savefig(buffer)

    return (normalite, corr, fig, buffer)


