-- marlinos Neovim: Tokyo Night, tree-sitter, LSP from the Arch repos, ~16 plugins.
-- Plugins come from vim.pack (built into Neovim 0.12), pinned by nvim-pack-lock.json in this
-- folder (committed): every machine runs the same revisions. :lua vim.pack.update() to upgrade.
vim.g.mapleader = " "
vim.g.maplocalleader = " "

require("marlinos.options")
require("marlinos.plugins")
require("marlinos.lsp")
require("marlinos.keymaps")
