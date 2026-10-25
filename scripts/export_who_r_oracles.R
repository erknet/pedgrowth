# WHO's anthro/anthroplus independently compute expected z-scores.
# Never call GrowthCharts for expected results. Input measurements are fixed.
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop('Usage: Rscript export_who_r_oracles.R INPUT OUTPUT')
if (!requireNamespace('anthro', quietly=TRUE) || !requireNamespace('anthroplus', quietly=TRUE)) stop('WHO R packages missing')
d <- read.csv(args[1], stringsAsFactors=FALSE)
d$expected <- NA_real_
d$engine <- NA_character_
for (i in seq_len(nrow(d))) {
  r <- d[i,]
  old <- grepl('^who2007_', r$table)
  sex <- r$sex
  age <- r$coordinate
  y <- r$measurement
  kind <- r$indicator
  if (old) {
    # WHO 2007 tables have native monthly indices.
    if (kind == 'hfa') {
      out <- anthroplus::anthroplus_zscores(sex=sex, age_in_months=age, height_in_cm=y, weight_in_kg=30)
      z <- out$zhfa
    } else if (kind == 'wfa') {
      out <- anthroplus::anthroplus_zscores(sex=sex, age_in_months=age, height_in_cm=130, weight_in_kg=y)
      z <- out$zwfa
    } else if (kind == 'bmifa') {
      out <- anthroplus::anthroplus_zscores(sex=sex, age_in_months=age, height_in_cm=100, weight_in_kg=y)
      z <- out$zbfa
    } else stop(paste('unsupported 2007', kind))
    engine <- 'WHO anthroplus'
  } else {
    # WHO 2006 age tables are normalized to months by GrowthCharts;
    # WHO anthro accepts age in days, and a measurement-position code.
    isage <- kind %in% c('wfa','lfa','hfa','hcfa','bmifa','muacfa','tsfa','ssfa')
    days <- if (isage) age*30.4375 else 365
    lenhei <- if (kind %in% c('lfa','hfa','wfl','wfh')) { if (kind %in% c('wfl','wfh')) age else y } else 80
    weight <- if (kind %in% c('wfa','wfl','wfh')) y else if (kind=='bmifa') y*(lenhei/100)^2 else 10
    out <- anthro::anthro_zscores(
      sex=sex, age=days, weight=weight, lenhei=lenhei,
      measure=if (kind %in% c('hfa','wfh') || (isage && days >= 731)) 'H' else 'L',
      headc=if (kind=='hcfa') y else 45,
      armc=if (kind=='muacfa') y else 15,
      triskin=if (kind=='tsfa') y else 10,
      subskin=if (kind=='ssfa') y else 10
    )
    key <- switch(kind, wfa='zwei',lfa='zlen',hfa='zlen',hcfa='zhc',bmifa='zbmi',
                  wfl='zwfl',wfh='zwfl',muacfa='zac',tsfa='zts',ssfa='zss')
    z <- out[[key]]
    engine <- 'WHO anthro'
  }
  d$expected[i] <- z
  d$engine[i] <- engine
}
d <- d[is.finite(d$expected),]
write.csv(d,args[2],row.names=FALSE,na='')
cat('WHO R reference calculations:',nrow(d),'\n')
