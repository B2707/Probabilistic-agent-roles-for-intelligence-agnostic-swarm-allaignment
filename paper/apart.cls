\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{apart}[2026/11/08 Apart Research Google Docs layout]
\LoadClass[11pt,letterpaper]{article}
\RequirePackage[letterpaper,margin=72bp,noheadfoot]{geometry}
\RequirePackage{fontspec}
\RequirePackage{xparse}
\RequirePackage{xcolor}
\RequirePackage[normalem]{ulem}
\renewcommand{\ULthickness}{1bp}
\ULdepth=.6bp
\RequirePackage{hyperref}
\RequirePackage{graphicx}
\RequirePackage{amsmath}
\RequirePackage{booktabs}
\setmainfont{OldStandard-Regular.ttf}[
  Path=fonts/,
  BoldFont=OldStandard-Bold.ttf,
  ItalicFont=OldStandard-Italic.ttf,
  BoldItalicFont=OldStandard-Italic.ttf,
  BoldItalicFeatures={FakeBold=3},
  Mapping=,
  Ligatures=NoCommon]
\IfFontExistsTF{Arial}{\newfontfamily\apartinfofont{Arial}}{\newfontfamily\apartinfofont{TeX Gyre Heros}}
\definecolor{ApartHeading}{HTML}{434343}
\definecolor{ApartSubheading}{HTML}{666666}
\definecolor{ApartInfo}{HTML}{FFF2CC}
\definecolor{ApartLink}{HTML}{1155CC}
\hypersetup{colorlinks=true,urlcolor=ApartLink,linkcolor=ApartLink,citecolor=ApartLink,
  pdftitle={Apart Research hackathon submission template}}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\setlength{\topskip}{10.982bp}
\setlength{\emergencystretch}{1em}
\hyphenpenalty=10000
\exhyphenpenalty=10000
\widowpenalty=0
\clubpenalty=0
\raggedbottom
\AtBeginDocument{%
  \fontsize{11bp}{15.6354bp}\selectfont
  \setbox\strutbox\hbox{\vrule height10.903bp depth4.7324bp width0pt}%
  \raggedright}
% Guidance is italic in the official Doc. Replace it with ordinary prose.
\newcommand{\guidance}[1]{\par\noindent\strut{\itshape #1}\strut\par}
\newcommand{\blankline}{\par\vspace{15.6354bp}}
\newcommand{\apart@heading}[1]{%
  \par\addvspace{9.925bp}\nointerlineskip
  \vbox{\hbox to\linewidth{%
    \vrule height13.972bp depth12.059bp width0pt
    {\fontsize{14bp}{26.031bp}\selectfont\bfseries\color{ApartHeading}#1}\hfil}}%
  \nobreak\nointerlineskip}
\newcommand{\apart@subheading}[1]{%
  \par\addvspace{10bp}\nointerlineskip
  \vbox{\hbox to\linewidth{%
    \vrule height13.1bp depth9.5bp width0pt
    {\fontsize{13bp}{22.6bp}\selectfont\bfseries\color{ApartSubheading}#1}\hfil}}%
  \nobreak\nointerlineskip}
\renewcommand{\section}{\@ifstar{\apart@heading}{\apart@numberedheading}}
\newcommand{\apart@numberedheading}[1]{\refstepcounter{section}\apart@heading{\thesection. #1}}
\renewcommand{\subsection}{\@ifstar{\apart@subheading}{\apart@numberedsubheading}}
\newcommand{\apart@numberedsubheading}[1]{\refstepcounter{subsection}\apart@subheading{\thesubsection\quad #1}}
% A Google Docs list has labels at +18bp and text at +36bp.
\newcommand{\apartitem}[2]{%
  \par\begingroup\advance\leftskip by36bp\parindent=-18bp
  \indent\strut\makebox[18bp][l]{\upshape #1}{\itshape #2}\strut\par\endgroup}
\newcommand{\apartalphaitem}[2]{%
  \par\begingroup\advance\leftskip by36bp\parindent=-18bp
  \indent\strut\makebox[18bp][l]{\itshape (#1)}{\itshape #2}\strut\par\endgroup}
\newenvironment{figuretips}{\par\begingroup\leftskip=30bp\rightskip=30bp}{\par\endgroup}
\newcommand{\ApartTitle}[1]{\def\aparttitle{#1}}
\newcommand{\ApartAuthors}[1]{\def\apartauthors{#1}}
\newcommand{\ApartAbstract}[1]{\def\apartabstract{#1}}
\newcommand{\ApartAuthor}[2]{#1\\#2}
% The optional third braced entry lets authors delete an unused slot safely.
\NewDocumentCommand{\ApartAuthorRow}{m m g}{%
  \IfNoValueTF{#3}{%
    \hbox to\linewidth{\hfil
      \parbox[t]{178.875bp}{\centering\fontsize{11bp}{13.596bp}\selectfont #1}%
      \parbox[t]{178.875bp}{\centering\fontsize{11bp}{13.596bp}\selectfont #2}\hfil}%
  }{%
    \hbox to\linewidth{\hfil
      \parbox[t]{119.25bp}{\centering\fontsize{11bp}{13.596bp}\selectfont #1}%
      \parbox[t]{119.25bp}{\centering\fontsize{11bp}{13.596bp}\selectfont #2}%
      \parbox[t]{119.25bp}{\centering\fontsize{11bp}{13.596bp}\selectfont #3}\hfil}%
  }}
\newif\ifApartGuidance
\ApartGuidancetrue
\newcommand{\ApartInstructionBox}{%
  \begingroup\apartinfofont\fontsize{12bp}{15.87bp}\selectfont
  \setlength{\fboxsep}{5.25bp}\setlength{\fboxrule}{.5bp}%
  \makebox[\linewidth][l]{\hspace*{-20bp}%
  \fcolorbox{black}{ApartInfo}{\parbox{507bp}{\raggedright\frenchspacing%
    \vspace{20.126bp}%
    \textbf{How to use this template}: Replace the \textit{italicized guidance text} under each section with your\\
    content. The section structure is strong guidance but not rigid. If your project requires a\\
    different organization, feel free to adapt. \uline{Delete all guidance text including this info box before}\\
    \uline{submitting}. Make sure the project title and author information above are up to date.\par
    \vspace{18bp}%
    \textbf{How your submission will be evaluated}: Your project will be judged on the quality of this\\
    written report. To understand what we look for, see our \href{https://apartresearch.notion.site/sprint-evaluation-rubric}{\uline{Evaluation Rubric}}.\par
    \vspace{18bp}%
    \textbf{Recommended length}: 4 pages excluding references and appendix.\\
    Rough guide: Intro \& Related Work 1p, Methods and Results: 2.5p, Discussion 0.5p.\par
    \vspace{9.669bp}}}}\par\endgroup}
% The title footnote is marked with an asterisk; template.tex, the official-layout copy, keeps the original 1.
\newcommand{\apart@ifreference}[2]{\ifdefined\ApartReferenceCopy#1\else#2\fi}
\newcommand{\MakeApartTitle}{%
  \par\nointerlineskip
  \vbox{\kern17bp\hrule height3bp\kern26.694bp
    \setbox0=\hbox{\fontsize{20bp}{24bp}\selectfont\bfseries
      \aparttitle\apart@ifreference{\raisebox{8.1576bp}{\fontsize{12bp}{12bp}\selectfont 1}}{*}}%
    \ifdim\wd0>\linewidth
      \hbox{\parbox{\linewidth}{\centering\fontsize{20bp}{24bp}\selectfont\bfseries
        \aparttitle\apart@ifreference{\textsuperscript{1}}{*}}}%
    \else\hbox to\linewidth{\hfil\box0\hfil}\fi
    \kern35.130bp\hrule height1bp\kern29.309bp
    \apartauthors
    \kern14.503bp
    \vbox{\baselineskip=13.596bp
      \hbox to\linewidth{\hfil\bfseries With\hfil}%
      \hbox to\linewidth{\hfil Apart Research\hfil}}%
    \kern22.955bp
    \hbox to\linewidth{\hfil{\fontsize{14bp}{17bp}\selectfont\bfseries Abstract}\hfil}%
    \kern20.365bp
    \hbox to\linewidth{\kern71.25bp\parbox{318bp}{%
      \fontsize{11bp}{13.596bp}\selectfont\itshape
      \frenchspacing\spaceskip=\fontdimen2\font plus3bp minus1bp
      \leftskip=0pt\rightskip=0pt\parfillskip=0pt plus1fil\apartabstract\par}\hfil}%
  }\par
  \ifApartGuidance\vspace{45.356bp}\ApartInstructionBox\fi
  \vfill
  \hrule width144bp height.75bp\vspace{8.125bp}
  {\fontsize{10bp}{12bp}\selectfont
    \apart@ifreference{\raisebox{4.0788bp}{\fontsize{6bp}{6bp}\selectfont 1}}{*}\hspace{2.8bp}Research conducted at the
    \href{https://apartresearch.com/sprints/swarm-alignment-2026}{\uline{Swarm Alignment Hackathon}}, November 2026\par}%
  \vspace{12.38bp}\newpage}
