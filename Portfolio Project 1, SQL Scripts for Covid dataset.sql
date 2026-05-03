Select *
From PortfolioProject..CovidDeaths
Where continent is not null
order by 3,4


--Select *
--From PortfolioProject..CovidVaccinations
--order by 3,4

--Select Location,date,total_cases,new_cases,total_deaths,population
--From PortfolioProject..CovidDeaths
--order by 1,2

--Looking at total cases vs total deaths
--Shows the likelihood of dying if you contract covid in United States

Select Location,date,total_cases,total_deaths, (Total_deaths/total_cases)*100 as DeathPercentage
From PortfolioProject..CovidDeaths
Where location like '%states'
order by 1,2

-- Looking at Total cases vs Population (Shows what percentage of population got covid)

Select Location,date,population,total_cases, (total_cases/population)*100 as CovidPercentage
From PortfolioProject..CovidDeaths
Where location like '%states'
order by 1,2

-- Looking at countries with highest infection rate compared to population

Select Location,population,MAX(total_cases) as HighestInfectionCount, Max((total_cases)/population)*100 as PercentPopulationInfected
From PortfolioProject..CovidDeaths
--Where location like '%states'
Group by Location,population
order by PercentPopulationInfected DESC

--Showing countries with highest death count per population (needs casting char to int

Select Location,MAX(cast(total_deaths as int)) as TotalDeathCount
From PortfolioProject..CovidDeaths
--Where location like '%states'
Where continent is not null
Group by Location
order by TotalDeathCount DESC

-- Lets break things down by continent

Select location, MAX(cast(Total_deaths as int)) as TotalDeathCount
From PortfolioProject..CovidDeaths
Where continent is null
Group by location
order by TotalDeathCount desc 

-- other approach (but this one only takes the largest from the individual countries (like US for NA))

Select continent, MAX(cast(Total_deaths as int)) as TotalDeathCount
From PortfolioProject..CovidDeaths
Where continent is not null
Group by continent
order by TotalDeathCount desc 

-- Showing continents with the highest death count per population

Select continent, MAX(cast(Total_deaths as int)) as TotalDeathCount
From PortfolioProject..CovidDeaths
Where continent is not null
Group by continent
order by TotalDeathCount desc

-- GLobal numbers 
Select date,SUM(new_cases) as Total_cases,SUM(cast(new_deaths as int)) as Total_deaths,SUM(cast(new_deaths as int))/SUM(New_cases) *100 as DeathPercentage
From PortfolioProject..CovidDeaths
--Where location like '%states'
where continent is not null
Group by date
order by 1,2

--Covid Vaccinations table

Select *
From PortfolioProject..CovidVaccinations


--join tables

Select *
From PortfolioProject..CovidDeaths dea
Join PortfolioProject..CovidVaccinations vac
	On dea.location = vac.location
	and dea.date = vac.date


-- Looking at Total Population vs Vaccinations


Select dea.continent,dea.location,dea.date, dea.population, vac.new_vaccinations, 
SUM(cast(vac.new_vaccinations as int)) OVER (Partition by dea.location order by dea.location,dea.Date) as "Rolling people Vaccinations"
From PortfolioProject..CovidDeaths dea
Join PortfolioProject..CovidVaccinations vac
	On dea.location = vac.location
	and dea.date = vac.date
where dea.continent is not null --and dea.location = 'canada'
order by 1,2,3

--CTE

With PopvsVac (Continent, Location, Date,Population,New_vaccinations, RollingPeopleVaccinated)
as
(
Select dea.continent,dea.location,dea.date, dea.population, vac.new_vaccinations, 
SUM(cast(vac.new_vaccinations as int)) OVER (Partition by dea.location order by dea.location,dea.Date) as "Rolling people Vaccinations"
From PortfolioProject..CovidDeaths dea
Join PortfolioProject..CovidVaccinations vac
	On dea.location = vac.location
	and dea.date = vac.date
where dea.continent is not null --and dea.location = 'canada'
--order by 1,2,3
)
Select *, (RollingPeopleVaccinated/Population)*100
From PopvsVac

--temp table
Drop Table if exists #PercentPopulationVaccinated
Create Table #PercentPopulationVaccinated
(
Continent nvarchar(255),
Location nvarchar(255),
Date datetime,
Population numeric,
New_vacccinations numeric,
RollingPeopleVaccinated numeric
)

insert into #PercentPopulationVaccinated
Select dea.continent,dea.location,dea.date, dea.population, vac.new_vaccinations, 
SUM(cast(vac.new_vaccinations as int)) OVER (Partition by dea.location order by dea.location,dea.Date) as "Rolling people Vaccinations"
From PortfolioProject..CovidDeaths dea
Join PortfolioProject..CovidVaccinations vac
	On dea.location = vac.location
	and dea.date = vac.date
where dea.continent is not null --and dea.location = 'canada'

Select *, (RollingPeopleVaccinated/Population)*100
From #PercentPopulationVaccinated

--view : to store data for later visualizations

Create view PercentPopulationVaccinated as 
Select dea.continent,dea.location,dea.date, dea.population, vac.new_vaccinations, 
SUM(cast(vac.new_vaccinations as int)) OVER (Partition by dea.location order by dea.location,dea.Date) as "Rolling people Vaccinations"
From PortfolioProject..CovidDeaths dea
Join PortfolioProject..CovidVaccinations vac
	On dea.location = vac.location
	and dea.date = vac.date
where dea.continent is not null

Select *
From PercentPopulationVaccinated