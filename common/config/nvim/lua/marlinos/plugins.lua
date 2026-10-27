local gh = function(repo) return "https://github.com/" .. repo end

-- tree-sitter parsers are compiled locally (tree-sitter-cli + cc): rebuild them after updates
vim.api.nvim_create_autocmd("PackChanged", {
  callback = function(ev)
    if ev.data.spec.name == "nvim-treesitter" and ev.data.kind ~= "delete" then
      vim.schedule(function() vim.cmd("TSUpdate") end)
    end
  end,
})

vim.pack.add({
  gh("folke/tokyonight.nvim"),
  { src = gh("nvim-treesitter/nvim-treesitter"), version = "main" },
  gh("nvim-treesitter/nvim-treesitter-context"),
  gh("neovim/nvim-lspconfig"), -- server definitions only (lsp/*.lua)
  { src = gh("saghen/blink.cmp"), version = vim.version.range("1") },
  gh("rafamadriz/friendly-snippets"),
  gh("ibhagwan/fzf-lua"),
  gh("nvim-tree/nvim-web-devicons"),
  gh("nvim-lualine/lualine.nvim"),
  gh("lewis6991/gitsigns.nvim"),
  gh("folke/which-key.nvim"),
  gh("stevearc/oil.nvim"),
  gh("stevearc/conform.nvim"),
  gh("echasnovski/mini.nvim"),
  gh("lukas-reineke/indent-blankline.nvim"),
  gh("j-hui/fidget.nvim"),
}, { confirm = false })

-- look -------------------------------------------------------------------------------------
require("tokyonight").setup({
  style = "night",
  styles = { comments = { italic = true }, keywords = { italic = true } },
  on_highlights = function(hl, c) hl.WinSeparator = { fg = c.border_highlight } end,
})
vim.cmd.colorscheme("tokyonight-night")

require("lualine").setup({
  options = {
    theme = "tokyonight",
    globalstatus = true,
    component_separators = "",
    section_separators = { left = "", right = "" },
  },
  sections = {
    lualine_a = { "mode" },
    lualine_b = { "branch", "diff", "diagnostics" },
    lualine_c = { { "filename", path = 1, symbols = { modified = " ●", readonly = " 󰌾" } } },
    lualine_x = { "lsp_status", "filetype" },
    lualine_y = { "progress" },
    lualine_z = { "location" },
  },
})

require("ibl").setup({ indent = { char = "│" }, scope = { enabled = true, show_start = false, show_end = false } })
require("fidget").setup({})
require("which-key").setup({ preset = "modern", delay = 300 })

-- code -------------------------------------------------------------------------------------
local parsers = {
  "bash", "c", "cpp", "css", "diff", "dockerfile", "fish", "git_config", "gitcommit", "go", "gomod",
  "html", "javascript", "json", "lua", "luadoc", "make", "markdown", "markdown_inline", "python",
  "query", "regex", "rust", "sql", "toml", "tsx", "typescript", "vim", "vimdoc", "yaml",
}
require("nvim-treesitter").install(parsers)
vim.api.nvim_create_autocmd("FileType", {
  callback = function(ev)
    if pcall(vim.treesitter.start, ev.buf) then
      vim.bo[ev.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
    end
  end,
})
require("treesitter-context").setup({ max_lines = 3 })

require("blink.cmp").setup({
  keymap = { preset = "default" }, -- C-y accept, C-n/C-p move, C-space open, C-e close
  appearance = { nerd_font_variant = "mono" },
  completion = {
    documentation = { auto_show = true, auto_show_delay_ms = 200 },
    menu = { draw = { treesitter = { "lsp" } } },
    ghost_text = { enabled = true },
  },
  signature = { enabled = true },
  sources = { default = { "lsp", "path", "snippets", "buffer" } },
  fuzzy = { implementation = "lua" }, -- no prebuilt binary to download
})

require("conform").setup({
  formatters_by_ft = {
    lua = { "stylua" },
    python = { "ruff_format", "ruff_organize_imports" },
    go = { "gofmt" },
    rust = { "rustfmt" },
    c = { "clang-format" },
    cpp = { "clang-format" },
    sh = { "shfmt" },
    bash = { "shfmt" },
    fish = { "fish_indent" },
    javascript = { "prettier" },
    typescript = { "prettier" },
    javascriptreact = { "prettier" },
    typescriptreact = { "prettier" },
    json = { "prettier" },
    yaml = { "prettier" },
    markdown = { "prettier" },
    css = { "prettier" },
    html = { "prettier" },
    toml = { "taplo" },
  },
  format_on_save = { timeout_ms = 1000, lsp_format = "fallback" },
})

require("gitsigns").setup({
  signs = { add = { text = "▎" }, change = { text = "▎" }, delete = { text = "" } },
  current_line_blame_opts = { delay = 300 },
})

require("mini.pairs").setup()
require("mini.surround").setup() -- sa / sd / sr: add, delete, replace surroundings
require("mini.ai").setup() -- better a/i text objects (functions, arguments...)

-- files -------------------------------------------------------------------------------------
require("oil").setup({ view_options = { show_hidden = true }, float = { padding = 4 } })
require("fzf-lua").setup({
  "telescope",
  winopts = { height = 0.85, width = 0.85, preview = { layout = "flex" } },
  files = { cwd_prompt = false },
})
require("fzf-lua").register_ui_select()
