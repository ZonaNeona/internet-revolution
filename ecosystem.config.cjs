module.exports = {
  apps: [
    {
      name: "demo-product-hunter-api",
      cwd: "/var/www/product-hunter",
      script: "/var/www/product-hunter/.venv/bin/python",
      args: "-m uvicorn backend.app:app --host 127.0.0.1 --port 3005",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
      env: {
        PRODUCT_HUNTER_ENV_FILE: "/etc/product-hunter.env"
      }
    },
    {
      name: "demo-product-hunter-worker",
      cwd: "/var/www/product-hunter",
      script: "/var/www/product-hunter/.venv/bin/python",
      args: "-m backend.worker",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 1000,
      env: {
        PRODUCT_HUNTER_ENV_FILE: "/etc/product-hunter.env"
      }
    }
  ]
};