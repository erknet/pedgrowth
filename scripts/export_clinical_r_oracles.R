# Publish-ready reproducible medical vignette inputs (no patient data).
# Independent R results from WHO anthro, WHO anthroplus, and CDC cdcanthro.
# Rows marked CDC_PUBLISHED_EXAMPLE also have external published expectations.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Expected clinical_cases_input.csv and output.csv")
if (!requireNamespace("anthro", quietly=TRUE) ||
    !requireNamespace("anthroplus", quietly=TRUE) ||
    !requireNamespace("cdcanthro", quietly=TRUE)) stop("Official anthropometry R packages required")

input <- read.csv(args[1L], stringsAsFactors=FALSE)
input$expected_z <- NA_real_
input$engine <- ""
cdc_ref_data <- cdcanthro::cdc_ref_data
# Evaluate CDC patients together: cdcanthro v0.4.0 treats some single-row
# whole-month inputs as the following half-month instead of interpolating.
# The multi-row call agrees with official CDC interpolation conventions.
cdc_rows <- which(input$reference == "cdc" & input$age >= 24)
cdc_cases <- input[cdc_rows, , drop=FALSE]
cdc_data <- data.frame(
  sex = ifelse(cdc_cases$sex == "M", 1, 2),
  age = cdc_cases$age,
  bmi = ifelse(cdc_cases$indicator == "bmifa", cdc_cases$measurement, 20),
  wt = ifelse(cdc_cases$indicator == "wfa", cdc_cases$measurement, 30),
  ht = ifelse(cdc_cases$indicator == "hfa", cdc_cases$measurement, 130)
)
cdc_result <- suppressWarnings(cdcanthro::cdc_z(
  cdc_data, age=age, wt=wt, ht=ht, bmi=bmi, all_vars=TRUE))
for (i in seq_len(nrow(input))) {
  row <- input[i, ]
  if (!is.finite(row$measurement) || row$measurement <= 0) stop("Invalid measurement")
  z <- NA_real_
  if (row$reference == "who") {
    days <- if (row$age_unit == "days") row$age else row$age * 30.4375
    # Measurement position is clinically meaningful for length and weight-for-length.
    lenhei <- if (row$indicator %in% c("lfa","hfa")) row$measurement else
      if (row$indicator %in% c("wfl","wfh")) row$coordinate else 80
    measure <- if (row$measured_position %in% c("L","H")) row$measured_position else
      if (days < 731) "L" else "H"
    weight <- if (row$indicator %in% c("wfa","wfl","wfh")) row$measurement else
      if (row$indicator == "bmifa") row$measurement * (lenhei/100)^2 else 10
    a <- anthro::anthro_zscores(
      sex=row$sex, age=days, weight=weight, lenhei=lenhei, measure=measure,
      headc=if (row$indicator=="hcfa") row$measurement else 45,
      armc=if (row$indicator=="muacfa") row$measurement else 14,
      triskin=if (row$indicator=="tsfa") row$measurement else 8,
      subskin=if (row$indicator=="ssfa") row$measurement else 6
    )
    key <- switch(row$indicator, wfa="zwei", lfa="zlen", hfa="zlen",
      hcfa="zhc", bmifa="zbmi", wfl="zwfl", wfh="zwfl",
      muacfa="zac", tsfa="zts", ssfa="zss")
    z <- a[[key]]
    input$engine[i] <- paste0("WHO anthro ", as.character(packageVersion("anthro")))
  } else if (row$reference == "who2007") {
    if (row$age_unit != "months") stop("WHO2007 months only")
    h <- if (row$indicator == "hfa") row$measurement else 100
    wt <- if (row$indicator %in% c("wfa", "bmifa")) row$measurement else 30
    a <- anthroplus::anthroplus_zscores(
      sex=row$sex, age_in_months=row$age, height_in_cm=h, weight_in_kg=wt)
    key <- switch(row$indicator, wfa="zwfa", hfa="zhfa", bmifa="zbfa")
    z <- a[[key]]
    input$engine[i] <- paste0("WHO anthroplus ",as.character(packageVersion("anthroplus")))
  } else if (row$reference == "cdc") {
    if (row$age_unit != "months") stop("CDC age inputs in months")
    if (row$age < 24) {
      # No infant WFA in cdcanthro. Official CDC published worked example
      # will be checked directly without claiming R independence for this row.
      if (row$id != "cdc-9mo-weight") stop("Unsupported CDC R infant chart")
      input$engine[i] <- "CDC published worked example only"
      next
    }
    key <- switch(row$indicator, bmifa="bmiz", wfa="waz", hfa="haz")
    z <- cdc_result[[key]][match(i, cdc_rows)]
    input$engine[i] <- paste0("CDC cdcanthro ", as.character(packageVersion("cdcanthro")))
  } else {
    stop(paste("Unknown reference family",row$reference))
  }
  input$expected_z[i] <- z
}
if (any(is.na(input$expected_z) & input$id != "cdc-9mo-weight")) {
  stop(paste("Unexpected nonfinite R output:",paste(input$id[is.na(input$expected_z)],collapse=",")))
}
write.csv(input,args[2],row.names=FALSE,na="")
cat("Independent clinical-vignette results:",sum(is.finite(input$expected_z)),
    "R outputs; 1 CDC published numerical example\n")
