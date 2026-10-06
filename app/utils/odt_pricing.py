def get_price_per_person_budhni(total_people: int , meal_preference : str ):
    print(meal_preference , total_people)
    if meal_preference == "with_meal":
        return 1099 
    else:
        return 869
def get_price_per_person_halali(total_people: int , meal_preference : str):
    print(meal_preference , total_people)
    if meal_preference == "with_meal":
        if total_people == 1:
            return 1199
        elif total_people <= 3:
            return 1165
        elif total_people <= 5:  
            return 1140
        else:   
            return 1115
    else:
        if total_people  == 1:
            return 1040
        elif total_people <= 3:
            return 1015
        elif total_people <= 5:
            return 999
        else:
            return 965
def get_price_per_person_ujjain(total_people: int , meal_preference : str):
    
    if meal_preference == "with_meal":
        if total_people == 1:
            return 5599
        elif total_people <= 3:
            return 5399
        else:   
            return 5199
    else:
        if total_people  == 1:
            return 4799
        elif total_people <= 3:
            return 4599
        else:
            return 4399

def get_price_per_person_heritage(total_people: int , meal_preference : str):
    if meal_preference == "with_meal":
        return 1099
    else:
       return 869