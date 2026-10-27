-- Language servers from the Arch repos (roles/dev/packages.txt); their settings come from
-- nvim-lspconfig's lsp/*.lua. A server that isn't installed is simply skipped.
local servers = {
  "lua_ls", "rust_analyzer", "gopls", "pyright", "ruff", "ts_ls", "clangd",
  "bashls", "yamlls", "marksman", "taplo",
}

vim.lsp.config("*", { capabilities = require("blink.cmp").get_lsp_capabilities() })
vim.lsp.config("lua_ls", {
  settings = { Lua = { workspace = { checkThirdParty = false, library = { vim.env.VIMRUNTIME } } } },
})
vim.lsp.config("rust_analyzer", {
  settings = { ["rust-analyzer"] = { check = { command = "clippy" } } },
})

for _, name in ipairs(servers) do
  local cmd = (vim.lsp.config[name] or {}).cmd
  if type(cmd) == "function" or (type(cmd) == "table" and vim.fn.executable(cmd[1]) == 1) then
    vim.lsp.enable(name)
  end
end

vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(ev)
    local client = vim.lsp.get_client_by_id(ev.data.client_id)
    -- types and parameter names inline, toggled with <leader>uh
    if client and client:supports_method("textDocument/inlayHint") then
      vim.lsp.inlay_hint.enable(true, { bufnr = ev.buf })
    end
  end,
})
