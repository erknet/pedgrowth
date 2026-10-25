# Independent reference calculations using the UNMODIFIED gigs v0.5.2 R source.
# The upstream R files are executed in an isolated R environment, not copied
# into the Python package. Source files must match the pinned SHA-256 values.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3L) {
  stop("Usage: Rscript export_intergrowth_gigs_r.R INPUT OUTPUT GIGS_SOURCE_DIRECTORY")
}
input <- args[1L]
output <- args[2L]
upstream <- args[3L]
if (!file.exists(file.path(upstream, "DESCRIPTION"))) stop("Missing original gigs source")
desc <- read.dcf(file.path(upstream, "DESCRIPTION"))
if (desc[1L, "Package"] != "gigs" || desc[1L, "Version"] != "0.5.2") {
  stop("Expected source from tagged gigs 0.5.2 release")
}

# Verify source file SHA-256 using system sha256sum (installed on CI Ubuntu).
expected_hashes <- c(
  "helpers.R" = "3a058e3dc6979a626e94a08efed36dcfd6963e7e2266f66c0470b053324e3529",
  "ig_png.R" = "609d37f02dd8ed6532a40313c8790a28fedf4b32491596aa15e603340bdc42cb",
  "ig_vpns.R" = "de0cfa424b881221cbbf633a11e783f53e09a30d151050954a9692f81e3cf8c8"
)
for (filename in names(expected_hashes)) {
  path <- file.path(upstream, "R", filename)
  if (!file.exists(path)) stop(paste("Missing upstream R source", filename))
  hash <- strsplit(
    system2("sha256sum", shQuote(path), stdout = TRUE), " ",
    fixed = TRUE
  )[[1L]][1L]
  if (hash != expected_hashes[[filename]]) stop(paste("gigs source hash mismatch", filename))
}

reference_env <- new.env(parent = baseenv())
for (filename in names(expected_hashes)) {
  sys.source(file.path(upstream, "R", filename), envir = reference_env)
}

d <- read.csv(input, stringsAsFactors = FALSE)
if (!all(d$sex %in% c("M", "F"))) stop("Unexpected sex codes")
if (!all(is.finite(d$coordinate) & is.finite(d$measurement) & d$measurement > 0)) {
  stop("Challenge measurements must be positive and finite")
}
d$expected <- NA_real_
for (fam in unique(d$family)) {
  for (indicator in unique(d$indicator[d$family == fam])) {
    which_rows <- which(d$family == fam & d$indicator == indicator)
    entries <- d[which_rows, , drop = FALSE]
    if (fam == "preterm_postnatal") {
      acr <- switch(indicator, weight = "wfa", length = "lfa",
        head_circumference = "hcfa", weight_for_length = "wfl")
      z <- reference_env$ig_png_v2z_internal(
        y = entries$measurement, x = entries$coordinate,
        sex = entries$sex, acronym = acr)
    } else if (fam == "very_preterm_birth") {
      acr <- switch(indicator, weight = "wfga", length = "lfga",
        head_circumference = "hcfga")
      z <- reference_env$ig_vpns_value2zscore(
        y = entries$measurement, gest_days = entries$coordinate,
        sex = entries$sex, acronym = acr)
    } else {
      stop(paste("Unrecognized INTERGROWTH family", fam))
    }
    d$expected[which_rows] <- z
  }
}
if (any(!is.finite(d$expected))) {
  stop("An eligible continuous INTERGROWTH test returned nonfinite R output")
}
write.csv(d, output, row.names = FALSE, na = "")
cat("Independent gigs source v0.5.2 calculations:", nrow(d),
    "indicators:", length(unique(paste(d$family, d$indicator))), "\n")
