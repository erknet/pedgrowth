# Validate the declared licenses AND exact versions of our independent
# R validation tools. This runs only on the GitHub Actions R validation
# runner, never in the pedgrowth runtime distribution.
#
# Optionally accept the original gigs 0.5.2 checkout as one argument.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 1L) stop("Expected no argument or one upstream gigs source directory")

versions <- c(anthro = "1.1.0", anthroplus = "1.1.0", cdcanthro = "0.4.0")
licenses <- c(anthro = "GPL-3", anthroplus = "GPL (>= 3)", cdcanthro = "GPL-3")
for (name in names(versions)) {
  if (!requireNamespace(name, quietly = TRUE)) {
    stop(paste("Required external R validator is absent:", name))
  }
  meta <- packageDescription(name)
  if (meta[["Version"]] != versions[[name]]) {
    stop(paste("External R validator version drift:", name, meta[["Version"]],
               "; expected", versions[[name]]))
  }
  if (meta[["License"]] != licenses[[name]]) {
    stop(paste("External R validator license drift:", name, meta[["License"]],
               "; expected", licenses[[name]]))
  }
  cat("Verified separate R reference tool:", name, meta[["Version"]],
      "under", meta[["License"]], "\n")
}
if (length(args) == 1L) {
  upstream <- args[1L]
  file <- file.path(upstream, "DESCRIPTION")
  if (!file.exists(file)) stop("Missing gigs package DESCRIPTION")
  meta <- read.dcf(file)[1L, ]
  if (meta[["Package"]] != "gigs" ||
      meta[["Version"]] != "0.5.2" ||
      meta[["License"]] != "GPL (>= 3)") {
    stop("Unexpected gigs identity/version/license: upstream validation not approved")
  }
  cat("Verified separate R reference tool:", meta[["Package"]], meta[["Version"]],
      "under", meta[["License"]], "\n")
}
