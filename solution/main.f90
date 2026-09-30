! Reference model for the corrosion survey.
!
! The counts are modelled against a log(length) offset — a Poisson GLM fitted by iteratively
! reweighted least squares. Fitting the observed rate (defects/length) directly instead lets a
! segment with 1 defect over 60 m carry the same weight as one with 500 over 30 km, and the
! graded deviance collapses.
program predictor
  implicit none
  integer, parameter :: dp = kind(1.0d0)
  integer, parameter :: NP = 9          ! intercept, age, cp, press, 2 coat, 3 soil
  integer :: ntr, nte, i, j, it
  character(len=16), allocatable :: id_tr(:), id_te(:)
  real(dp), allocatable :: Xtr(:,:), Xte(:,:), ytr(:), yte(:), offtr(:), offte(:)
  real(dp) :: b(NP), eta, mu, w, z, A(NP,NP), rhs(NP), pred
  real(dp), allocatable :: Wv(:), Zv(:)

  call load('/app/data/history.dat', .true.,  Xtr, ytr, offtr, id_tr, ntr)
  call load('/app/data/survey.dat',  .false., Xte, yte, offte, id_te, nte)

  b = 0.0_dp
  b(1) = log(max(sum(ytr), 1.0_dp) / max(sum(offtr), 1.0e-9_dp))

  allocate(Wv(ntr), Zv(ntr))
  do it = 1, 40
     do i = 1, ntr
        eta = dot_product(Xtr(i,:), b) + log(offtr(i))
        eta = max(min(eta, 30.0_dp), -30.0_dp)
        mu  = exp(eta)
        mu  = max(mu, 1.0e-9_dp)
        Wv(i) = mu
        Zv(i) = dot_product(Xtr(i,:), b) + (ytr(i) - mu) / mu
     end do
     A = 0.0_dp; rhs = 0.0_dp
     do i = 1, ntr
        do j = 1, NP
           rhs(j) = rhs(j) + Wv(i) * Xtr(i,j) * Zv(i)
           A(j,:) = A(j,:) + Wv(i) * Xtr(i,j) * Xtr(i,:)
        end do
     end do
     do j = 1, NP
        A(j,j) = A(j,j) + 1.0e-8_dp
     end do
     call solve(A, rhs, b, NP)
  end do

  open(unit=20, file='/app/out/predictions.dat', status='replace', action='write')
  write(20,'(A)') 'seg_id expected_defects'
  do i = 1, nte
     eta = dot_product(Xte(i,:), b) + log(offte(i))
     eta = max(min(eta, 30.0_dp), -30.0_dp)
     pred = exp(eta)
     write(20,'(A,1X,F0.6)') trim(id_te(i)), pred
  end do
  close(20)
  write(*,'(A,I0,A)') 'wrote /app/out/predictions.dat (', nte, ' segments)'

contains

  ! Read the export into a design matrix. Categorical levels are one-hot with the first level
  ! (fbe, sand) as the baseline, matching the order the data dictionary lists them in.
  subroutine load(path, has_y, X, y, off, ids, n)
    character(len=*), intent(in) :: path
    logical, intent(in) :: has_y
    real(dp), allocatable, intent(out) :: X(:,:), y(:), off(:)
    character(len=16), allocatable, intent(out) :: ids(:)
    integer, intent(out) :: n
    character(len=256) :: line
    character(len=16) :: sid, coat, soil
    real(dp) :: len_km, age, cp, press
    integer :: cnt, u, ios, k
    u = 10
    open(unit=u, file=path, status='old', action='read')
    read(u,'(A)') line
    n = 0
    do
       read(u,'(A)',iostat=ios) line
       if (ios /= 0) exit
       if (len_trim(line) > 0) n = n + 1
    end do
    rewind(u); read(u,'(A)') line
    allocate(X(n,NP), y(n), off(n), ids(n))
    X = 0.0_dp; y = 0.0_dp
    do k = 1, n
       if (has_y) then
          read(u,*) sid, len_km, age, cp, coat, soil, press, cnt
          y(k) = real(cnt, dp)
       else
          read(u,*) sid, len_km, age, cp, coat, soil, press
       end if
       ids(k)  = sid
       off(k)  = len_km
       X(k,1)  = 1.0_dp
       X(k,2)  = age
       X(k,3)  = cp + 880.0_dp
       X(k,4)  = press - 62.0_dp
       if (trim(coat) == 'tape') X(k,5) = 1.0_dp
       if (trim(coat) == 'cte')  X(k,6) = 1.0_dp
       if (trim(soil) == 'clay') X(k,7) = 1.0_dp
       if (trim(soil) == 'loam') X(k,8) = 1.0_dp
       if (trim(soil) == 'peat') X(k,9) = 1.0_dp
    end do
    close(u)
  end subroutine load

  ! Gaussian elimination with partial pivoting.
  subroutine solve(Ain, bin, xout, m)
    integer, intent(in) :: m
    real(dp), intent(in) :: Ain(m,m), bin(m)
    real(dp), intent(out) :: xout(m)
    real(dp) :: A(m,m+1), f, tmp(m+1)
    integer :: i, j, p
    A(:,1:m) = Ain; A(:,m+1) = bin
    do i = 1, m
       p = i
       do j = i+1, m
          if (abs(A(j,i)) > abs(A(p,i))) p = j
       end do
       if (p /= i) then
          tmp = A(i,:); A(i,:) = A(p,:); A(p,:) = tmp
       end if
       do j = i+1, m
          f = A(j,i) / A(i,i)
          A(j,:) = A(j,:) - f * A(i,:)
       end do
    end do
    do i = m, 1, -1
       xout(i) = (A(i,m+1) - dot_product(A(i,i+1:m), xout(i+1:m))) / A(i,i)
    end do
  end subroutine solve

end program predictor
