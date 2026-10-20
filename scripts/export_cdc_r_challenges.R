args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop('Usage: export_cdc_r_challenges.R INPUT OUTPUT')
if (!requireNamespace('cdcanthro', quietly=TRUE)) stop('CDC cdcanthro R package missing')
# Compatibility with cdcanthro 0.4.0 exported data-table NSE.
cdc_ref_data <- cdcanthro::cdc_ref_data
d <- read.csv(args[1], stringsAsFactors=FALSE)
if (!all(d$sex %in% c(1,2))) stop('Invalid CDC sex codes')
r <- suppressWarnings(cdcanthro::cdc_z(
  data.frame(sex=d$sex, age=d$age, bmi=d$bmi),
  age=age, bmi=bmi
))
d$expected <- r$bmiz
write.csv(d,args[2], row.names=FALSE, na='')
cat('CDC R BMI outputs:',nrow(d),'available',sum(is.finite(d$expected)),'\n')
