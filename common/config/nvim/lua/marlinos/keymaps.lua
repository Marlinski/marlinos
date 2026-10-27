-- <space> is the leader; press it and wait: which-key lists everything below.
-- Built in already: K hover, grn rename, gra code action, grr references, gri implementation,
-- gO symbols, [d ]d diagnostics, gc comment, C-s signature.
local map = function(mode, lhs, rhs, desc) vim.keymap.set(mode, lhs, rhs, { desc = desc }) end
local fzf = require("fzf-lua")

map("n", "<Esc>", "<cmd>nohlsearch<cr>", "Clear search highlight")
map("n", "<C-h>", "<C-w>h", "Window left")
map("n", "<C-j>", "<C-w>j", "Window down")
map("n", "<C-k>", "<C-w>k", "Window up")
map("n", "<C-l>", "<C-w>l", "Window right")
map("n", "<S-h>", "<cmd>bprevious<cr>", "Previous buffer")
map("n", "<S-l>", "<cmd>bnext<cr>", "Next buffer")
map("v", "<", "<gv", "Indent left")
map("v", ">", ">gv", "Indent right")
map("n", "-", "<cmd>Oil<cr>", "Files (parent dir)")

-- find
map("n", "<leader><space>", fzf.files, "Find files")
map("n", "<leader>/", fzf.live_grep, "Grep")
map("n", "<leader>,", fzf.buffers, "Buffers")
map("n", "<leader>fr", fzf.oldfiles, "Recent files")
map("n", "<leader>fw", fzf.grep_cword, "Grep word under cursor")
map("n", "<leader>fh", fzf.helptags, "Help")
map("n", "<leader>fk", fzf.keymaps, "Keymaps")
map("n", "<leader>f.", fzf.resume, "Resume last search")

-- code
map("n", "gd", fzf.lsp_definitions, "Go to definition")
map("n", "<leader>cs", fzf.lsp_document_symbols, "Symbols (file)")
map("n", "<leader>cS", fzf.lsp_live_workspace_symbols, "Symbols (project)")
map("n", "<leader>cd", fzf.diagnostics_document, "Diagnostics (file)")
map("n", "<leader>cD", fzf.diagnostics_workspace, "Diagnostics (project)")
map({ "n", "v" }, "<leader>cf", function() require("conform").format({ lsp_format = "fallback" }) end, "Format")
map("n", "<leader>cl", function() vim.diagnostic.open_float() end, "Line diagnostics")
map("n", "<leader>uh", function() vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled()) end, "Toggle inlay hints")

-- git
local gs = require("gitsigns")
map("n", "]h", function() gs.nav_hunk("next") end, "Next hunk")
map("n", "[h", function() gs.nav_hunk("prev") end, "Previous hunk")
map("n", "<leader>gs", gs.stage_hunk, "Stage hunk")
map("n", "<leader>gr", gs.reset_hunk, "Reset hunk")
map("n", "<leader>gp", gs.preview_hunk, "Preview hunk")
map("n", "<leader>gb", gs.toggle_current_line_blame, "Toggle line blame")
map("n", "<leader>gd", gs.diffthis, "Diff file")
map("n", "<leader>gc", fzf.git_commits, "Commits")
map("n", "<leader>gS", fzf.git_status, "Status")

require("which-key").add({
  { "<leader>f", group = "find" }, { "<leader>c", group = "code" },
  { "<leader>g", group = "git" }, { "<leader>u", group = "toggle" },
})
