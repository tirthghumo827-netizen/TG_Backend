def get_price_per_person_budhni(total_people: int , meal_preference : str):
    print(meal_preference , total_people)
    if meal_preference == "with_meal":
        if total_people == 1:
            return 1351
        elif total_people <= 3:
            return 1301
        elif total_people <= 5:  
            return 1275
        else:   
            return 1251
    else:
        if total_people  == 1:
            return 1201
        elif total_people <= 3:
            return 1151
        elif total_people <= 5:
            return 1125
        else:
            return 1101
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