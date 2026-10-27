local o = vim.opt

o.number = true
o.relativenumber = true
o.signcolumn = "yes"
o.cursorline = true
o.scrolloff = 8
o.sidescrolloff = 8
o.wrap = false
o.showmode = false -- lualine shows it
o.laststatus = 3 -- one statusline for all windows
o.cmdheight = 1
o.pumheight = 12
o.winborder = "rounded"
o.splitright = true
o.splitbelow = true
o.list = true
o.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
o.fillchars = { eob = " " }
o.mouse = "a"
o.clipboard = "unnamedplus" -- wl-clipboard
o.undofile = true
o.swapfile = false
o.ignorecase = true
o.smartcase = true
o.inccommand = "split"
o.updatetime = 250
o.timeoutlen = 400
o.expandtab = true
o.shiftwidth = 4
o.tabstop = 4
o.smartindent = true
o.confirm = true

-- the usual widths per language
vim.api.nvim_create_autocmd("FileType", {
  pattern = { "lua", "javascript", "typescript", "javascriptreact", "typescriptreact", "json", "yaml", "html", "css", "nix", "toml" },
  callback = function() vim.bo.shiftwidth = 2; vim.bo.tabstop = 2 end,
})
vim.api.nvim_create_autocmd("FileType", {
  pattern = { "go", "make" },
  callback = function() vim.bo.expandtab = false end,
})

-- flash what was yanked
vim.api.nvim_create_autocmd("TextYankPost", { callback = function() vim.hl.on_yank({ timeout = 150 }) end })

-- back to the last position when reopening a file
vim.api.nvim_create_autocmd("BufReadPost", {
  callback = function(ev)
    local mark = vim.api.nvim_buf_get_mark(ev.buf, '"')
    if mark[1] > 0 and mark[1] <= vim.api.nvim_buf_line_count(ev.buf) then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})

vim.diagnostic.config({
  severity_sort = true,
  virtual_text = { spacing = 2, prefix = "●" },
  float = { border = "rounded", source = true },
  signs = {
    text = {
      [vim.diagnostic.severity.ERROR] = " ",
      [vim.diagnostic.severity.WARN] = " ",
      [vim.diagnostic.severity.INFO] = " ",
      [vim.diagnostic.severity.HINT] = "󰌵 ",
    },
  },
})
