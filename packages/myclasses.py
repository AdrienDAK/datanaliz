import pandas as pd
import numpy as np
import scipy.stats as stat
from sklearn.model_selection import cross_val_score
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn import linear_model
from docx import  Document
import scipy.stats as stat
import pandas as pd
import seaborn as sns
from io import BytesIO
import numpy as np
import pingouin as pg
import textwrap
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scikit_posthocs import posthoc_dunn as pdunn
from streamlit import dataframe



import rpy2
from matplotlib.style.core import library
from rpy2.robjects import pandas2ri
from rpy2.robjects import default_converter
import rpy2.robjects.packages as rpackages
from rpy2.robjects.packages import importr


class MakeAnalysis():
    """
    This class is intended to carry out every analysis to be done. Its methods have different roles.
    """
    def __init__(self, data, analyses):
        self.data = data
        self.analyses = analyses

    def affiche_pvalue(self,pv):
        """
        :param pv: Une valeur décimale telle qu'une p-value
        :return: une valeur décimale arrondie à 3 chiffres si pv est ≥0.001 ou le caractère <0.001 dans
            le cas contraire. pv reste inchangé s'il est un caractère.
        """
        try:
            if float(pv) < 0.001:
                return "<0.001"
            else:
                return round(float(pv), 3)

        except:
            return pv

    def add_df_to_doc(self,df, doc, title):
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


    def khi2(self,var_ligne, var_colonne):
        """ Cette fonction réalise le test du Chi 2 entre deux variables : colonne et ligne
                Le résultat est un tableau croisé dans lequel l'on a en colonnes les modalités
                    de la variable colonne et en lignes les variables lignes et leurs modalités respectives.

                Les paramètres sont les suivants :
                    - var_colonne : une des colonnes de 'df', correspondant à une variable qualitative
                    - ligne : une des colonnes de 'df', différente de la précédente qualitative également

                Le résultat de la fonction est un dataframe comportant le tableau croisé des 2 variables et deux autres colonnes
                affichant le nombre de degrés de liberté et la p-value du test

            """

        d = self.data.copy()
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
        #stats = importr('stats')
        #p_fisher = stats.fisher_test(cont.to_numpy())[0][0]

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
                if i * j / total_general < 5 :
                    nb_eff_5 += 1

        tableau['Stat Khi-2'] = chi2
        tableau['DL'] = DL
        tableau['P-value Khi 2'] = PV

        with (rpy2.robjects.default_converter + pandas2ri.converter).context():
            r_cont = rpy2.robjects.conversion.get_conversion().py2rpy(cont)
            stats = importr("stats")
            p_fisher = stats.fisher_test(r_cont)["p.value"][0]
            p_khi2_r = stats.chisq_test(r_cont)["p.value"][0]

        if nb_eff_5:
            PV_fisher = [''] * len(cont)
            PV_fisher[0] = ".".join([elt[:4] for elt in str(round(p_fisher, 4)).split(".")])
            tableau['p-value Fisher'] = PV_fisher


        return (tableau, nb_eff_5)

    def anova(self, groupes, valeurs, input_report):
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

        		Le résultat de la fonction est une liste [norm_homocedastic, valeurs_par_groupe_anova, comment, test_norm, key,input_report,post_hoc_res] :
        			- norm_homocedastic est un dataframe contenant les résultats des tests d'homocédasticité et de normalité
        			- valeurs_par_groupe_anova est le tableau contenant les valeurs moyennes par groupes et les résultats des comparaisons
                    - comment est un ensemble de commentaires inhérents aux résultats des tests de comparaison
                    - test_norm : est le "nom" du test de normalité utilisé. Il est fonction due la taille de l'échantillon
                    - key est le nom du test de comparaison utilisé, compte tenu des résultats des tests de normalité et d'homocédasticité
                    - input_report est le document fourni en argument, dans lequel ont été insérés les résultats
                    - post_hoc_res est un dataframe contenant les résultats de l'analyse post hoc, s'il y en a
        	"""
        comment = list()
        graphiques = []
        data = self.data

        test = {'kruskal': stat.kruskal,
                'anova': stat.f_oneway,
                "mannwhitney": stat.mannwhitneyu,
                "student": stat.ttest_ind}

        ################### Tests de normalité et d'homocédasticité #######################
        data_notna = data[data[valeurs].notna()]
        p_value_normalite = self.affiche_pvalue(stat.shapiro(data_notna[valeurs])[1])

        p = input_report.add_paragraph('Boxplot')
        l = data[groupes].unique()
        l.sort()
        arrays = [list(data_notna[data_notna[groupes] == groupe][valeurs]) for groupe in l]

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

        p_value_homocedast = self.affiche_pvalue(stat.bartlett(*arrays)[1])

        norm_homocedastic = pd.DataFrame({"normality": [p_value_normalite], "homocedasticity": [p_value_homocedast]})

        table = input_report.add_table(rows=1, cols=2, style='LightShading-Accent1')

        hdr_cells = table.rows[0].cells

        hdr_cells[0].text = 'p normality'
        hdr_cells[1].text = 'p homocédasticity'
        row_cells = table.add_row().cells
        row_cells[0].text = str(p_value_normalite)
        row_cells[1].text = str(p_value_homocedast)

        if len(list(data[groupes].unique())) == 2:
            if isinstance(p_value_normalite, str) or isinstance(p_value_homocedast, str):
                key = 'mannwhitney'
            elif p_value_normalite > 0.05 and p_value_homocedast > 0.05:
                key = "student"
            else:
                key = 'mannwhitney'

        else:

            if not (isinstance(p_value_normalite, str) or isinstance(p_value_homocedast,
                                                                     str)) and p_value_normalite > 0.05 and p_value_homocedast > 0.05:
                key = "anova"
            else:
                key = 'kruskal'
        input_report.add_paragraph("The Shapiro-Wilk test was implemented to check the normality of the data.")

        if isinstance(p_value_normalite, str) or isinstance(p_value_homocedast, str):
            input_report.add_paragraph(
                "Non-parametric tests are implemented, even though the conditions of normality and equality of variances are not met.")
        elif float(p_value_normalite) > 0.05 and float(p_value_homocedast) > 0.05:
            input_report.add_paragraph(
                "Parametric tests are implemented since the conditions of normality and equality of variances are met.")
        elif float(p_value_normalite) < 0.05 and float(p_value_homocedast) > 0.05:
            input_report.add_paragraph(
                "Non-parametric tests are implemented since the normality condition is not met.")
        elif float(p_value_normalite) > 0.05 and float(p_value_homocedast) < 0.05:
            input_report.add_paragraph(
                "Non-parametric tests are implemented since the condition of equality of variances is not met.")
        else:
            input_report.add_paragraph(
                "Non-parametric tests are implemented since the conditions of normality and equality of variances are not met."
            )

        #################### Comparaison des groupes  #########################################

        comment = []
        donnees_anova = []
        lignes = []
        moyenne = []
        ecart_type = []
        minimum = []
        median = []
        maximum = []
        l = data[groupes].unique()
        l.sort()
        for gr in l:
            donnees_anova.append(list(data[data[groupes] == gr][valeurs]))
            lignes.append(gr)
            moyenne.append(round(np.nanmean(list(data[data[groupes] == gr][valeurs])), 3))
            ecart_type.append(round(np.nanstd(list(data[data[groupes] == gr][valeurs])), 3))
            minimum.append(round(np.nanmin(list(data[data[groupes] == gr][valeurs])), 3))
            median.append(round(np.nanmedian(list(data[data[groupes] == gr][valeurs])), 3))
            maximum.append(round(np.nanmax(list(data[data[groupes] == gr][valeurs])), 3))

        valeurs_par_groupe_anova = pd.DataFrame(
            {groupes: lignes, 'Mean': moyenne, 'Standard deviation': ecart_type, 'Minimum': minimum,
             'Median': median, 'Maximum': maximum})

        anova = [''] * len(valeurs_par_groupe_anova)
        anova[0] = round(test[key](*donnees_anova, nan_policy='omit')[0], 3)

        PV = [''] * len(valeurs_par_groupe_anova)
        PV[0] = self.affiche_pvalue(test[key](*donnees_anova, nan_policy='omit')[1])

        valeurs_par_groupe_anova['Stat'] = anova
        valeurs_par_groupe_anova['P-value'] = PV

        # Ajout du tableau dans le document word
        p = input_report.add_paragraph('')
        p = input_report.add_paragraph(
            'Comparaison: variable {} according to variable {}'.format(valeurs, groupes))

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

            if len(list(data[groupes].unique())) <= 2:
                # Commentaires
                com = f"The p-value of the {key} test is less than 5%. Therefore, we have good reason to believe that some groups have different means. Since the independent variable has only two categories, performing a post-hoc analysis is meaningless."
                #input_report.add_paragraph(com)
                comment.append(com)

            else:

                if key == 'kruskal':
                    # p = input_report.add_paragraph('Analyse post hoc : test de Dunn')
                    # Commentaires
                    comment.append(
                        "The p-value is less than 5%. Therefore, we have good reason to believe that some groups have different means.")
                    comment.append(
                        "We must now perform a post hoc analysis to determine which groups have different means.")
                    comment.append("The Dunn test is used for the post hoc analysis.")
                else:
                    # Commentaires
                    comment.append(
                        "The p-value is less than 5%. Therefore, we have good reason to believe that some groups have different means.")
                    comment.append(
                        "We must now perform a post hoc analysis to identify the groups whose means are different.")
                    comment.append("Post hoc analysis: t-test")

                    p = input_report.add_paragraph('Post hoc analysis: t-test')

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
                                {groupes: lignes, 'Mean': moyenne, 'Standard deviation': ecart_type, 'Minimum': minimum,
                                 'Median': median, 'Maximum': maximum})

                            PV = [''] * len(valeurs_par_groupe_post)
                            PV[0] = self.affiche_pvalue(post_hoc_res[l[i]][l[j]])
                            valeurs_par_groupe_post['P-value'] = PV

                            self.add_df_to_doc(valeurs_par_groupe_post, input_report, " ")

                            if post_hoc_res[l[i]][l[j]] > 0.05:
                                comment.append(
                                    "There is no significant difference between {} and {}.".format(l[i], l[j]))
                            else:
                                comment.append(
                                    "At the 5% significance level, there is a significant difference between {} and {}.".format(
                                        l[i],
                                        l[j]))
                res = post_hoc_res.copy()

                post_hoc_res = pd.DataFrame()
                for col in res.columns:
                    try:
                        post_hoc_res[col] = res[col].astype(float).apply(lambda x: self.affiche_pvalue(x))
                    except:
                        post_hoc_res[col] = res[col]

        else:
            input_report.add_paragraph("The groups are not significantly different.")

        commentaires = str()
        for com in comment:
            commentaires += com
            input_report.add_paragraph(com)
        comment = commentaires
        comment = comment[:-1]

        test_norm = "Shapiro-Wilk"

        try:
            return [norm_homocedastic, valeurs_par_groupe_anova, comment, test_norm, key, input_report, post_hoc_res]
        except:
            return [norm_homocedastic, valeurs_par_groupe_anova, comment, test_norm, key, input_report]

