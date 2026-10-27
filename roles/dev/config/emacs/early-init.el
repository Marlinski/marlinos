;;; early-init.el --- marlinos: before the first frame -*- lexical-binding: t -*-
;; No package downloads, no toolbars, dark from the first frame (no white flash).
(setq package-enable-at-startup nil
      gc-cons-threshold (* 64 1024 1024)
      inhibit-startup-screen t
      frame-inhibit-implied-resize t)
(push '(menu-bar-lines . 0) default-frame-alist)
(push '(tool-bar-lines . 0) default-frame-alist)
(push '(vertical-scroll-bars) default-frame-alist)
(push '(internal-border-width . 14) default-frame-alist)
(push '(background-color . "#1a1b26") default-frame-alist)
(push '(foreground-color . "#c0caf5") default-frame-alist)
(push '(font . "JetBrainsMono Nerd Font-11") default-frame-alist)
