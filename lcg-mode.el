;;; lcg-mode.el -- Mode for editing LCG source exercise files

;; Copyright (C) 2005, 2006 Brailcom, o.p.s.

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

;; LCG is a Learning Content Generator.
;; See http://www.freebsoft.org/lcg.

;; This mode does some basic syntax highlighting for LCG exercise definition
;; files.

;; To start using lcg-mode, copy this file into your Emacs library path and add
;; this in your .emacs file:
;; (load-library "lcg-mode")

(defvar lcg-mode-version "$Id"
  "The version of lcg-mode currently loaded")

(defvar lcg-args 
  '("reading" "instructions" "explanation" "example" "audio_version"
    "sound_file" "transcript" "reading_instructions" "template" "pieces"))

(defun lcg-list-2-regexp(altlist)
  "Takes a list and returns the regexp \\(elem1\\|elem2\\|...\\)"
  (let ((regexp "\\("))
    (mapcar (lambda(elem) (setq regexp (concat regexp elem "\\|"))) altlist)
    (concat (substring regexp 0 -2) "\\)") ; cutting the last "\\|"
    ))

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
    ; exercise type definition
    (list "^\\(type:\\) \\(.*\\)$" 
	  '(1 'font-lock-variable-name-face)
	  '(2 'font-lock-keyword-face)) 
    ; header arguments
    (list (concat "^\\(" (lcg-list-2-regexp lcg-args) ":\\) \\(.*\\)$")
	  '(1 'font-lock-variable-name-face)
	  '(2 'font-lock-string-face)) 
    ; multiline header arguments
    (list (concat "^\\(</?" (lcg-list-2-regexp lcg-args) ">\\)")
	  0 'font-lock-variable-name-face)
    ))
  "Expressions to highlight in LCG exercise definition files.")

(define-derived-mode lcg-mode text-mode "LCG"
  "Major mode for editing LCG exercise definition files."
  (set (make-local-variable 'font-lock-defaults)
       '(lcg-font-lock-keywords
	 nil t nil nil 
	 (font-lock-syntactic-keywords . lcg-font-lock-syntactic-keywords)))
  (setq major-mode 'lcg-mode
	fill-column 79)
  (run-hooks 'lcg-mode-hook))

(provide 'lcg-mode)
