# Independent source audit, not a legal clearance.
#
# Compare the original numerical WHO 2006/2007 LMS coefficients embedded in
# WHO's GPL-licensed anthro / anthroplus packages with the coefficients which
# pedgrowth derives from official WHO downloads. Only a numerical count/report
# is emitted; no upstream R code or tables are copied into the Python runtime.

who_2006 <- c(
  weight_for_age = "growthstandards_weianthro",
  length_for_age = "growthstandards_lenanthro",
  bmi_for_age = "growthstandards_bmianthro",
  head_circumference_for_age = "growthstandards_hcanthro",
  muac_for_age = "growthstandards_acanthro",
  subscapular_for_age = "growthstandards_ssanthro",
  triceps_for_age = "growthstandards_tsanthro",
  weight_for_height = "growthstandards_wfhanthro",
  weight_for_length = "growthstandards_wflanthro"
)
who_2007 <- c(
  weight_for_age = "wfa_growth_standards",
  height_for_age = "hfa_growth_standards",
  bmi_for_age = "bfa_growth_standards"
)

if (!requireNamespace("anthro", quietly = TRUE) ||
    !requireNamespace("anthroplus", quietly = TRUE)) {
  stop("Requires the original WHO anthro and anthroplus R packages")
}
all_files <- sort(list.files("validation/source_data", pattern = "^who.*\\.csv$", full.names = TRUE))
if (length(all_files) != 24L) {
  stop("Expected precisely the 24 WHO reference data tables")
}

results <- data.frame(
  table = character(), rows = integer(), matched = integer(),
  outside_R_domain = integer(), mismatched = integer()
)
for (file in all_files) {
  key <- sub("\\.csv$", "", basename(file))
  is_2007 <- startsWith(key, "who2007_")
  sex <- if (grepl("_boys$", key)) 1L else 2L
  chart <- sub("^who2007_|^who_", "", key)
  chart <- sub("_(boys|girls)$", "", chart)

  if (is_2007) {
    r_table_name <- who_2007[[chart]]
    namespace <- asNamespace("anthroplus")
  } else {
    r_table_name <- who_2006[[chart]]
    namespace <- asNamespace("anthro")
  }
  if (is.null(r_table_name) || !exists(r_table_name, envir = namespace, inherits = FALSE)) {
    stop(paste("Missing official WHO R coefficient table:", key))
  }
  r_table <- get(r_table_name, envir = namespace, inherits = FALSE)
  r_table <- r_table[r_table$sex == sex, , drop = FALSE]
  current <- read.csv(file, stringsAsFactors = FALSE)

  if (is_2007) {
    coordinate <- current$index
    r_coordinate <- "age"
  } else if (chart == "weight_for_length") {
    coordinate <- current$index
    r_coordinate <- "length"
  } else if (chart == "weight_for_height") {
    coordinate <- current$index
    r_coordinate <- "height"
  } else {
    # pedgrowth's WHO child ages are represented as fractional months from
    # WHO's integer-day source values, using the documented 30.4375 d/month.
    coordinate <- round(current$index * 30.4375)
    r_coordinate <- "age"
    if (any(abs(current$index * 30.4375 - coordinate) > 1e-7)) {
      stop(paste("Non-integer age-day mapping in", key))
    }
  }

  idx <- match(coordinate, r_table[[r_coordinate]])
  included <- !is.na(idx)
  upstream <- r_table[idx, , drop = FALSE]
  matched <- included &
    abs(current$l - upstream$l) < 1e-9 &
    abs(current$m - upstream$m) < 1e-9 &
    abs(current$s - upstream$s) < 1e-9
  matched[is.na(matched)] <- FALSE
  mismatched <- sum(included & !matched)
  if (mismatched != 0L) {
    stop(paste("Published WHO R coefficients disagree with pedgrowth:", key))
  }
  results <- rbind(
    results,
    data.frame(
      table = key,
      rows = nrow(current),
      matched = sum(matched),
      outside_R_domain = sum(!included),
      mismatched = mismatched
    )
  )
}

matching <- sum(results$matched)
outside <- sum(results$outside_R_domain)
if (matching != 28228L || outside != 420L || sum(results$mismatched) != 0L) {
  stop(
    paste(
      "WHO R reference overlap changed: matched", matching,
      "outside R domain", outside, "mismatched", sum(results$mismatched)
    )
  )
}
cat(
  "Original WHO R package coefficient provenance: 24/24 tables,",
  matching, "identical LMS records,", outside,
  "WHO 2006 reference records outside the R-supported age limits;",
  "zero numerical mismatches\n"
)
