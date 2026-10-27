;;; init.el --- marlinos: a good-looking Emacs from built-ins only -*- lexical-binding: t -*-
;; Nothing to download: everything here ships with Emacs 31.

;;; look: modus-vivendi tinted towards Tokyo Night
(setq modus-themes-italic-constructs t
      modus-themes-bold-constructs t
      modus-themes-mixed-fonts t
      modus-themes-common-palette-overrides
      '((bg-main "#1a1b26") (bg-dim "#16161e") (bg-alt "#1f2335")
        (fg-main "#c0caf5") (fg-dim "#a9b1d6")
        (bg-mode-line-active "#24283b") (fg-mode-line-active "#c0caf5")
        (bg-mode-line-inactive "#16161e") (border-mode-line-active unspecified)
        (border-mode-line-inactive unspecified)
        (bg-line-number-inactive bg-main) (bg-line-number-active bg-main)
        (fg-line-number-active "#7aa2f7") (bg-hl-line "#292e42")
        (comment "#565f89") (string "#9ece6a") (keyword "#bb9af7")
        (fnname "#7aa2f7") (variable "#c0caf5") (type "#2ac3de") (constant "#ff9e64")
        (cursor "#7aa2f7") (bg-region "#283457") (fringe unspecified)))
(load-theme 'modus-vivendi t)
(set-face-attribute 'variable-pitch nil :family "Noto Sans" :height 1.0)

(setq-default cursor-type 'bar
              line-spacing 0.15
              fill-column 100
              indent-tabs-mode nil
              tab-width 4)
(global-display-line-numbers-mode 1)
(dolist (h '(term-mode-hook eshell-mode-hook shell-mode-hook))
  (add-hook h (lambda () (display-line-numbers-mode -1))))
(global-hl-line-mode 1)
(pixel-scroll-precision-mode 1)
(column-number-mode 1)
(blink-cursor-mode -1)
(setq ring-bell-function #'ignore
      use-short-answers t
      display-line-numbers-width 3)

;;; behaviour
(setq make-backup-files nil
      auto-save-default nil
      create-lockfiles nil
      custom-file (locate-user-emacs-file "custom.el")
      scroll-margin 4
      scroll-conservatively 101)
(load custom-file 'noerror)
(save-place-mode 1)
(savehist-mode 1)
(recentf-mode 1)
(global-auto-revert-mode 1)
(electric-pair-mode 1)
(delete-selection-mode 1)
(editorconfig-mode 1)
(which-key-mode 1)

;;; completion: vertical minibuffer, inline preview, fuzzy-ish matching
(fido-vertical-mode 1)
(global-completion-preview-mode 1)
(setq completion-styles '(basic partial-completion flex)
      completions-detailed t
      tab-always-indent 'complete)

;;; code: tree-sitter modes when the grammar is there, eglot for languages servers
(setq treesit-enabled-modes t)
(setq eglot-autoshutdown t)
(dolist (h '(python-ts-mode-hook go-ts-mode-hook rust-ts-mode-hook c-ts-mode-hook
             c++-ts-mode-hook js-ts-mode-hook typescript-ts-mode-hook))
  (add-hook h #'eglot-ensure))
(add-hook 'prog-mode-hook #'flymake-mode)

;;; keys you'd expect
(keymap-global-set "C-x C-b" #'ibuffer)
(keymap-global-set "C-c f" #'recentf-open)
(keymap-global-set "C-c p" #'project-find-file)
(keymap-global-set "C-c g" #'project-find-regexp)
