;;; structured-text-mode.el -- Mode for editing LCG structured text files

;; Copyright (C) 2006 OUI Technology Ltd.
;; Copyright (C) 2019-2024 Tomáš Cerha <t.cerha@gmail.com>

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

;; LCG is a framework for accessible content generation.
;; See http://www.freebsoft.org/lcg for more information.

;; This mode does some very simple regexp based syntax highlighting.
;; To start using structured-text-mode, put this in your .emacs file:
;; (load "structured-text-mode")

(defvar structured-text-mode-version "$Id"
  "The version of structured-text-mode currently loaded")

;; Font lock
(defconst structured-text-font-lock-keywords
  (purecopy
   (list
    (list "^#.*$" 0 'font-lock-comment-face t)            ; comments
    ;(list "^[ \t].*$" 0 'font-lock-string-face t)         ; preformatted text
    ;(list "^[\\*\\|0]+ .*$" 0 'font-lock-string-face t)   ; itemized lists
    (list "\\[.*\\]"        0 'font-lock-warning-face)    ; links
    (list "^\\(@TOC@\\)\\s-*$" 1 'font-lock-builtin-face) ; TOC
    (list "^=+ \\(.*?\\) =+$" ; headers
	  1 'font-lock-keyword-face)
    (list "^=+ \\(.*?\\) =+[ \t]+\\([A-Za-z0-9_-]+\\|\\*\\)$" ; headers
	  '(1 'font-lock-keyword-face)
	  '(2 'font-lock-variable-name-face))
    ; TODO: the following regexps don't work on multiline text
    (list "\\(?:\\W\\|^\\)\\*\\(\\S-\\(.*?\\S-\\)?\\)\\*\\W"
	  1 'font-lock-function-name-face t) ; bold
    (list "\\(?:\\W\\|^\\)/\\(\\S-\\(.*?\\S-\\)?\\)/\\W"
	  1 'font-lock-comment-face t) ; italic
    (list "\\(?:\\W\\|^\\)=\\(\\S-\\(.*?\\S-\\)?\\)=\\W"
	  1 'font-lock-string-face) ; fixed font
    ))
  "Expressions to highlight in structured text.")

(define-derived-mode structured-text-mode text-mode "Structured Text"
  "Major mode for editing LCG structured text files."
  (set (make-local-variable 'font-lock-defaults)
       '(structured-text-font-lock-keywords
	 nil t))
  (setq major-mode 'structured-text-mode
	fill-column 79)
  (run-hooks 'structured-text-mode-hook))

(provide 'structured-text-mode)
