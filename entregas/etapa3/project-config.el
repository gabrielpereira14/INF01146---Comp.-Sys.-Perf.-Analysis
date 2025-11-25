;; --- Package System ---
(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(package-initialize)

;; Install use-package if needed
(unless (package-installed-p 'use-package)
  (package-refresh-contents)
  (package-install 'use-package))

(require 'use-package)

;; --- Org-mode + Babel Python ---
(use-package org
  :ensure t
  :config
  ;; Enable Python execution in Org-babel
  (org-babel-do-load-languages
   'org-babel-load-languages
   '((python . t)))

  (setq org-babel-python-command "python3")
  (setq org-confirm-babel-evaluate nil)

  ;; Display images automatically after executing blocks
  (add-hook 'org-babel-after-execute-hook
            'org-display-inline-images
            'append))

;; Allow exporting using Babel blocks
(setq org-export-use-babel t)