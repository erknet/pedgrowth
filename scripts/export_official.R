# External numerical comparison against WHO/CDC's independent R implementations.
# CRAN packages: anthroplus (WHO) and cdcanthro (CDC).
# Run after: install.packages(c("anthroplus", "cdcanthro"))
# Usage: Rscript --vanilla scripts/export_official.R /tmp/official-values.csv

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Expected one output CSV path")

if (!requireNamespace("anthroplus", quietly = TRUE) ||
    !requireNamespace("cdcanthro", quietly = TRUE)) {
  stop("Install the WHO anthroplus and CDC cdcanthro R packages first")
}

# cdcanthro 0.4.0 currently refers to its exported table by a free symbol
# inside data.table expressions; bind it in the caller to avoid an NSE lookup error.
cdc_ref_data <- cdcanthro::cdc_ref_data

set.seed(23)
result <- data.frame(
  standard = character(), indicator = character(), age = numeric(),
  sex = character(), measurement = numeric(), expected = numeric()
)

add <- function(standard, indicator, age, sex, measurement, expected) {
  sample <- data.frame(
    standard = standard, indicator = indicator, age = age,
    sex = sex, measurement = measurement, expected = expected
  )
  sample <- sample[!is.na(sample$expected) & is.finite(sample$expected), ]
  result <<- rbind(result, sample)
}

# Exact WHO 2007 monthly coordinates, plus age-in-between interpolation cases.
# Weight-for-age stops at 120 months by WHO design.
for (sex in c("M", "F")) {
  ages <- c(61, 72.5, 91, 100, 119, 120, 145.5, 180, 200, 228)
  heights <- c(109, 116, 127, 132, 145, 149, 163, 172, 176, 178) +
    ifelse(sex == "F", -2, 0)
  weights <- c(18, 21, 25, 30, 38, 41, 51, 64, 68, 71) +
    ifelse(sex == "F", -1, 0)
  who <- anthroplus::anthroplus_zscores(
    sex = rep(sex, length(ages)), age_in_months = ages,
    height_in_cm = heights, weight_in_kg = weights
  )
  add("who", "hfa", ages, sex, heights, who$zhfa)
  add("who", "wfa", ages, sex, weights, who$zwfa)
  add("who", "bmifa", ages, sex, weights / (heights / 100)^2, who$zbfa)
}

# CDC package computes extended BMI above the official P95 and LMS below it.
for (sex in c("M", "F")) {
  ages <- c(24.5, 50.5, 51, 92.5, 114.5, 184.5, 238.5)
  for (offset in c(-3, 0, 5, 13)) {
    bmi <- c(17, 17, 18, 19, 22, 28, 31) + offset
    inputs <- data.frame(sex = ifelse(sex == "M", 1, 2),
                         age = ages, bmi = bmi)
    cdc <- suppressWarnings(cdcanthro::cdc_z(inputs, age = age, bmi = bmi))
    add("cdc", "bmifa", ages, sex, bmi, cdc$bmiz)
  }
}

if (nrow(result) < 85) stop("Unexpectedly small independent reference set")
write.csv(result, file = args[1], row.names = FALSE, na = "")
cat("Independent WHO/CDC calculations:", nrow(result), "observations\n")
