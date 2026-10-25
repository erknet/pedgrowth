# Independent WHO Anthro check of recumbent/standing 0.7 cm correction.
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop('Usage: export_who_r_positions.R INPUT OUTPUT')
if (!requireNamespace('anthro', quietly=TRUE)) stop('WHO anthro R package required')
d <- read.csv(args[1],stringsAsFactors=FALSE)
out <- anthro::anthro_zscores(
    sex=d$sex, age=d$age_days,
    weight=d$weight_kg, lenhei=d$lenhei_cm, measure=d$measure)
d$expected_length_height_z <- out$zlen
d$expected_weight_for_size_z <- out$zwfl
write.csv(d,args[2],row.names=FALSE,na='')
cat('WHO R position conversions:',nrow(d),'\n')
