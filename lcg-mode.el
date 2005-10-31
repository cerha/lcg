;;; lcg-mode.el -- Mode for editing LCG source files

;; Copyright (C) 2005 Tomas Cerha

;; This file is not part of GNU Emacs.

;; This is free software; you can redistribute it and/or modify it under
;; the terms of the GNU General Public License as published by the Free
;; Software Foundation; either version 2, or (at your option) any later
;; version.
;;
;; This is distributed in the hope that it will be useful, but WITHOUT
;; ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
;; FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
;; for more details.
;;
;; You should have received a copy of the GNU General Public License
;; along with GNU Emacs; see the file COPYING.  If not, write to the
;; Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
;; MA 02111-1307, USA.

;;; Commentary:

;; LCG is a Learning Content Generator.
;; See http://www.freebsoft.org/lcg.

;; This mode does some basic syntax highlighting for LCG exercise definition
;; files.

;; * Startup

;; To begin using lcg-mode, copy this file into your Emacs library path and add
;; this in your .emacs file:

;; (load-library "lcg-mode")

(defvar lcg-mode-version "$Id"
  "The version of lcg-mode currently loaded")

(defvar lcg-font-lock-syntactic-keywords
  '(("^<[a-z_-]+>\\([ \t\n\r]\\)"  (1 '(15)))
    ("\\([\n\r]\\)</[a-z_-]+>" (1 '(15)))
    ;; the first number refers the a match group within the regexp and the
    ;; later is Emacs Syntax table category.
    )
  "Syntactic keywords to catch multiline args in `lcg-mode'.")

;; Font lock
(defconst lcg-font-lock-keywords
  (purecopy
   (list
    (list "^.?# -\\*- .* -\\*-"  0 'font-lock-builtin-face) ; first line
    (list "^#.*$"                0 'font-lock-comment-face t) ; comments
    (list "^[-=]\\{4,\\}[\t ]*$" 0 'font-lock-function-name-face t) ; separators
    (list "\\[.*?\\]"            0 'font-lock-warning-face) ; fill-in text
    (list "^=+ \\(.*?\\) =+$" ; section headers
	  1 'font-lock-function-name-face)
    (list "^\\(type:\\) \\(.*\\)$" ; exercise type definition
	  '(1 'font-lock-variable-name-face)
	  '(2 'font-lock-keyword-face)) 
    (list "^\\([a-z_-]+:\\) \\(.*\\)$" ; other header arguments
	  '(1 'font-lock-variable-name-face)
	  '(2 'font-lock-string-face)) 
    (list "^\\(</?\\(reading\\|instructions\\|explanation\\|example\\|reading_instructions\\|\\)>\\)"
	  0 'font-lock-variable-name-face)
    ))
  "Expressions to highlight in LCG exercise definition files.")

(defun lcg-mode ()
  "Major mode for editing LCG exercise definition files."
  (interactive)
  (kill-all-local-variables)
  (set (make-local-variable 'font-lock-defaults)
       '(lcg-font-lock-keywords
	 nil t nil nil 
	 (font-lock-syntactic-keywords . lcg-font-lock-syntactic-keywords)))
  (setq major-mode 'lcg-mode
	mode-name "LCG"
	fill-column 79)
  (run-hooks 'lcg-mode-hook))

(provide 'lcg-mode)
